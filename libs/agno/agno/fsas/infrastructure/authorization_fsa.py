"""
Authorization FSA (Finite State Automaton) for the Agno MLA Framework.

This module provides a comprehensive production-ready authorization system with:
- Role-Based Access Control (RBAC) with hierarchical roles
- Attribute-Based Access Control (ABAC) with policy engine
- Permission management (create, read, update, delete, execute)
- Resource-level authorization with granular permissions
- Policy evaluation engine with rule composition
- Integration with Authentication FSA
- Session-based and token-based authorization
- Audit logging for all authorization decisions
- Caching for performance optimization
- Support for dynamic permission grants/revokes
- Multi-tenant authorization support

Author: Agno Team
License: MIT
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from pydantic import BaseModel, Field, validator


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class AuthorizationState(str, Enum):
    """Authorization FSA states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    AUTHORIZING = "authorizing"
    AUTHORIZED = "authorized"
    UNAUTHORIZED = "unauthorized"
    EVALUATING_POLICY = "evaluating_policy"
    CHECKING_PERMISSION = "checking_permission"
    VALIDATING_ROLE = "validating_role"
    CHECKING_RESOURCE = "checking_resource"
    CACHING = "caching"
    LOGGING = "logging"
    ERROR = "error"
    SUSPENDED = "suspended"


class Permission(str, Enum):
    """Standard permission types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    GRANT = "grant"
    REVOKE = "revoke"
    LIST = "list"
    SEARCH = "search"
    EXPORT = "export"
    IMPORT = "import"


class PolicyEffect(str, Enum):
    """Policy evaluation effects."""

    ALLOW = "allow"
    DENY = "deny"


class PolicyOperator(str, Enum):
    """Policy rule operators."""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    MATCHES = "matches"
    EXISTS = "exists"


class AuditAction(str, Enum):
    """Audit log action types."""

    AUTHORIZE = "authorize"
    DENY = "deny"
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"
    CREATE_ROLE = "create_role"
    DELETE_ROLE = "delete_role"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"
    CREATE_POLICY = "create_policy"
    DELETE_POLICY = "delete_policy"
    EVALUATE_POLICY = "evaluate_policy"


# ============================================================================
# DATA MODELS
# ============================================================================


class AuthorizationContext(BaseModel):
    """Context for authorization decisions."""

    user_id: str
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    token: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class Resource(BaseModel):
    """Resource model for authorization."""

    resource_id: str
    resource_type: str
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class Role(BaseModel):
    """Role model with hierarchical support."""

    role_id: str
    name: str
    description: Optional[str] = None
    tenant_id: Optional[str] = None
    permissions: Set[str] = Field(default_factory=set)
    parent_roles: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

    def __hash__(self):
        return hash(self.role_id)


class PolicyRule(BaseModel):
    """Individual policy rule for ABAC."""

    attribute: str
    operator: PolicyOperator
    value: Any

    class Config:
        arbitrary_types_allowed = True


class Policy(BaseModel):
    """Authorization policy for ABAC."""

    policy_id: str
    name: str
    description: Optional[str] = None
    tenant_id: Optional[str] = None
    effect: PolicyEffect
    resources: List[str] = Field(default_factory=list)  # Resource types or IDs
    actions: List[str] = Field(default_factory=list)  # Permissions
    rules: List[PolicyRule] = Field(default_factory=list)
    priority: int = 0  # Higher priority policies evaluated first
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


class PermissionGrant(BaseModel):
    """Explicit permission grant."""

    grant_id: str
    user_id: str
    resource_id: str
    permission: str
    tenant_id: Optional[str] = None
    granted_by: str
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class AuditLogEntry(BaseModel):
    """Audit log entry for authorization events."""

    log_id: str
    action: AuditAction
    user_id: str
    tenant_id: Optional[str] = None
    resource_id: Optional[str] = None
    permission: Optional[str] = None
    result: bool
    reason: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


class AuthorizationResult(BaseModel):
    """Result of an authorization check."""

    authorized: bool
    user_id: str
    resource_id: Optional[str] = None
    permission: Optional[str] = None
    reason: Optional[str] = None
    matched_policies: List[str] = Field(default_factory=list)
    matched_roles: List[str] = Field(default_factory=list)
    evaluation_time_ms: float = 0.0
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# CACHE MANAGER
# ============================================================================


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    key: str
    value: Any
    created_at: float
    ttl: float  # Time to live in seconds
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """Update hit count."""
        self.hits += 1


class CacheManager:
    """Cache manager for authorization decisions."""

    def __init__(self, default_ttl: float = 300.0, max_size: int = 10000):
        """
        Initialize cache manager.

        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum cache size
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def _generate_key(self, *args: Any) -> str:
        """Generate cache key from arguments."""
        key_str = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, *args: Any) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            *args: Cache key components

        Returns:
            Cached value or None
        """
        key = self._generate_key(*args)
        entry = self.cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        entry.touch()
        self.hits += 1
        return entry.value

    def set(self, value: Any, *args: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.

        Args:
            value: Value to cache
            *args: Cache key components
            ttl: Time-to-live in seconds
        """
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        key = self._generate_key(*args)
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl or self.default_ttl
        )

    def invalidate(self, *args: Any) -> None:
        """
        Invalidate cache entry.

        Args:
            *args: Cache key components
        """
        key = self._generate_key(*args)
        self.cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].hits)
        del self.cache[lru_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }


# ============================================================================
# POLICY ENGINE
# ============================================================================


class PolicyEngine:
    """Policy evaluation engine for ABAC."""

    def __init__(self):
        """Initialize policy engine."""
        self.policies: Dict[str, Policy] = {}
        self.operators: Dict[PolicyOperator, Callable] = {
            PolicyOperator.EQUALS: lambda a, b: a == b,
            PolicyOperator.NOT_EQUALS: lambda a, b: a != b,
            PolicyOperator.GREATER_THAN: lambda a, b: a > b,
            PolicyOperator.LESS_THAN: lambda a, b: a < b,
            PolicyOperator.GREATER_EQUAL: lambda a, b: a >= b,
            PolicyOperator.LESS_EQUAL: lambda a, b: a <= b,
            PolicyOperator.IN: lambda a, b: a in b,
            PolicyOperator.NOT_IN: lambda a, b: a not in b,
            PolicyOperator.CONTAINS: lambda a, b: b in a,
            PolicyOperator.MATCHES: lambda a, b: self._regex_match(a, b),
            PolicyOperator.EXISTS: lambda a, b: a is not None,
        }

    def _regex_match(self, value: str, pattern: str) -> bool:
        """Match value against regex pattern."""
        import re
        try:
            return bool(re.match(pattern, str(value)))
        except Exception:
            return False

    def add_policy(self, policy: Policy) -> None:
        """
        Add policy to engine.

        Args:
            policy: Policy to add
        """
        self.policies[policy.policy_id] = policy

    def remove_policy(self, policy_id: str) -> None:
        """
        Remove policy from engine.

        Args:
            policy_id: Policy ID to remove
        """
        self.policies.pop(policy_id, None)

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy or None
        """
        return self.policies.get(policy_id)

    def evaluate_rule(self, rule: PolicyRule, context: Dict[str, Any]) -> bool:
        """
        Evaluate a single policy rule.

        Args:
            rule: Policy rule to evaluate
            context: Evaluation context

        Returns:
            True if rule matches
        """
        try:
            attribute_value = context.get(rule.attribute)
            operator_func = self.operators.get(rule.operator)

            if operator_func is None:
                return False

            return operator_func(attribute_value, rule.value)
        except Exception:
            return False

    def evaluate_policy(
        self,
        policy: Policy,
        resource: Optional[Resource],
        permission: str,
        context: AuthorizationContext
    ) -> bool:
        """
        Evaluate a policy against context.

        Args:
            policy: Policy to evaluate
            resource: Resource being accessed
            permission: Permission being checked
            context: Authorization context

        Returns:
            True if policy matches (all conditions met), regardless of effect
        """
        if not policy.enabled:
            return False

        # Check if policy applies to this resource
        if policy.resources:
            if resource is None:
                return False

            resource_match = False
            for policy_resource in policy.resources:
                if policy_resource == "*" or policy_resource == resource.resource_type:
                    resource_match = True
                    break
                if policy_resource == resource.resource_id:
                    resource_match = True
                    break

            if not resource_match:
                return False

        # Check if policy applies to this action
        if policy.actions:
            if permission not in policy.actions and "*" not in policy.actions:
                return False

        # Evaluate all rules
        eval_context = {
            "user_id": context.user_id,
            "tenant_id": context.tenant_id,
            "session_id": context.session_id,
            "ip_address": context.ip_address,
            "timestamp": context.timestamp,
            **context.attributes
        }

        if resource:
            eval_context.update({
                "resource_id": resource.resource_id,
                "resource_type": resource.resource_type,
                "resource_owner": resource.owner_id,
                **{f"resource_{k}": v for k, v in resource.attributes.items()}
            })

        for rule in policy.rules:
            if not self.evaluate_rule(rule, eval_context):
                return False

        # All conditions met - policy matches
        return True

    def evaluate_policies(
        self,
        resource: Optional[Resource],
        permission: str,
        context: AuthorizationContext,
        tenant_id: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate all applicable policies.

        Args:
            resource: Resource being accessed
            permission: Permission being checked
            context: Authorization context
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Tuple of (authorized, matched_policy_ids)
        """
        matched_policies = []

        # Sort policies by priority (highest first)
        sorted_policies = sorted(
            self.policies.values(),
            key=lambda p: p.priority,
            reverse=True
        )

        allow = False
        deny = False

        for policy in sorted_policies:
            # Check tenant isolation
            if tenant_id and policy.tenant_id and policy.tenant_id != tenant_id:
                continue

            if self.evaluate_policy(policy, resource, permission, context):
                matched_policies.append(policy.policy_id)

                if policy.effect == PolicyEffect.ALLOW:
                    allow = True
                elif policy.effect == PolicyEffect.DENY:
                    deny = True
                    break  # Explicit deny takes precedence

        # Deny takes precedence over allow
        authorized = allow and not deny

        return authorized, matched_policies


# ============================================================================
# ROLE MANAGER
# ============================================================================


class RoleManager:
    """Manager for RBAC with hierarchical roles."""

    def __init__(self):
        """Initialize role manager."""
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, Set[str]] = defaultdict(set)
        self.role_hierarchy: Dict[str, Set[str]] = defaultdict(set)

    def add_role(self, role: Role) -> None:
        """
        Add role to manager.

        Args:
            role: Role to add
        """
        self.roles[role.role_id] = role
        self._update_hierarchy(role)

    def remove_role(self, role_id: str) -> None:
        """
        Remove role from manager.

        Args:
            role_id: Role ID to remove
        """
        self.roles.pop(role_id, None)
        self.role_hierarchy.pop(role_id, None)

        # Remove from user assignments
        for user_id in self.user_roles:
            self.user_roles[user_id].discard(role_id)

    def get_role(self, role_id: str) -> Optional[Role]:
        """
        Get role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role or None
        """
        return self.roles.get(role_id)

    def assign_role(self, user_id: str, role_id: str) -> None:
        """
        Assign role to user.

        Args:
            user_id: User ID
            role_id: Role ID
        """
        if role_id in self.roles:
            self.user_roles[user_id].add(role_id)

    def remove_role_from_user(self, user_id: str, role_id: str) -> None:
        """
        Remove role from user.

        Args:
            user_id: User ID
            role_id: Role ID
        """
        self.user_roles[user_id].discard(role_id)

    def get_user_roles(self, user_id: str) -> Set[str]:
        """
        Get all roles assigned to user.

        Args:
            user_id: User ID

        Returns:
            Set of role IDs
        """
        return self.user_roles.get(user_id, set())

    def _update_hierarchy(self, role: Role) -> None:
        """
        Update role hierarchy.

        Args:
            role: Role to update hierarchy for
        """
        self.role_hierarchy[role.role_id] = set(role.parent_roles)

    def get_all_inherited_roles(self, role_id: str) -> Set[str]:
        """
        Get all inherited roles including parents recursively.

        Args:
            role_id: Role ID

        Returns:
            Set of all role IDs including inherited
        """
        inherited = {role_id}
        visited = set()

        def traverse(rid: str) -> None:
            if rid in visited:
                return
            visited.add(rid)

            parents = self.role_hierarchy.get(rid, set())
            for parent in parents:
                inherited.add(parent)
                traverse(parent)

        traverse(role_id)
        return inherited

    def get_effective_permissions(self, user_id: str) -> Set[str]:
        """
        Get all effective permissions for user including inherited.

        Args:
            user_id: User ID

        Returns:
            Set of permission strings
        """
        permissions = set()
        user_roles = self.get_user_roles(user_id)

        for role_id in user_roles:
            all_roles = self.get_all_inherited_roles(role_id)
            for rid in all_roles:
                role = self.get_role(rid)
                if role:
                    permissions.update(role.permissions)

        return permissions

    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if user has permission through roles.

        Args:
            user_id: User ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        effective_permissions = self.get_effective_permissions(user_id)
        return permission in effective_permissions or "*" in effective_permissions


# ============================================================================
# PERMISSION MANAGER
# ============================================================================


class PermissionManager:
    """Manager for explicit permission grants."""

    def __init__(self):
        """Initialize permission manager."""
        self.grants: Dict[str, PermissionGrant] = {}
        self.user_grants: Dict[str, Set[str]] = defaultdict(set)
        self.resource_grants: Dict[str, Set[str]] = defaultdict(set)

    def grant_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        granted_by: str,
        tenant_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PermissionGrant:
        """
        Grant permission to user for resource.

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to grant
            granted_by: ID of user granting permission
            tenant_id: Tenant ID
            expires_at: Expiration time
            metadata: Additional metadata

        Returns:
            Created permission grant
        """
        grant = PermissionGrant(
            grant_id=str(uuid4()),
            user_id=user_id,
            resource_id=resource_id,
            permission=permission,
            tenant_id=tenant_id,
            granted_by=granted_by,
            expires_at=expires_at,
            metadata=metadata or {}
        )

        self.grants[grant.grant_id] = grant
        self.user_grants[user_id].add(grant.grant_id)
        self.resource_grants[resource_id].add(grant.grant_id)

        return grant

    def revoke_permission(self, grant_id: str) -> bool:
        """
        Revoke permission grant.

        Args:
            grant_id: Grant ID to revoke

        Returns:
            True if revoked
        """
        grant = self.grants.pop(grant_id, None)
        if grant:
            self.user_grants[grant.user_id].discard(grant_id)
            self.resource_grants[grant.resource_id].discard(grant_id)
            return True
        return False

    def has_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str
    ) -> bool:
        """
        Check if user has explicit permission for resource.

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        grant_ids = self.user_grants.get(user_id, set())

        for grant_id in grant_ids:
            grant = self.grants.get(grant_id)
            if not grant:
                continue

            # Check expiration
            if grant.expires_at and datetime.utcnow() > grant.expires_at:
                continue

            if grant.resource_id == resource_id and grant.permission == permission:
                return True

        return False

    def get_user_grants(self, user_id: str) -> List[PermissionGrant]:
        """
        Get all grants for user.

        Args:
            user_id: User ID

        Returns:
            List of permission grants
        """
        grant_ids = self.user_grants.get(user_id, set())
        return [self.grants[gid] for gid in grant_ids if gid in self.grants]

    def get_resource_grants(self, resource_id: str) -> List[PermissionGrant]:
        """
        Get all grants for resource.

        Args:
            resource_id: Resource ID

        Returns:
            List of permission grants
        """
        grant_ids = self.resource_grants.get(resource_id, set())
        return [self.grants[gid] for gid in grant_ids if gid in self.grants]

    def cleanup_expired_grants(self) -> int:
        """
        Remove expired grants.

        Returns:
            Number of grants removed
        """
        now = datetime.utcnow()
        expired = []

        for grant_id, grant in self.grants.items():
            if grant.expires_at and now > grant.expires_at:
                expired.append(grant_id)

        for grant_id in expired:
            self.revoke_permission(grant_id)

        return len(expired)


# ============================================================================
# AUDIT LOGGER
# ============================================================================


class AuditLogger:
    """Audit logger for authorization events."""

    def __init__(self, max_entries: int = 100000):
        """
        Initialize audit logger.

        Args:
            max_entries: Maximum log entries to keep in memory
        """
        self.max_entries = max_entries
        self.logs: List[AuditLogEntry] = []
        self.log_handlers: List[Callable[[AuditLogEntry], None]] = []

    def add_handler(self, handler: Callable[[AuditLogEntry], None]) -> None:
        """
        Add log handler.

        Args:
            handler: Handler function
        """
        self.log_handlers.append(handler)

    def log(
        self,
        action: AuditAction,
        user_id: str,
        result: bool,
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        permission: Optional[str] = None,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """
        Log authorization event.

        Args:
            action: Action type
            user_id: User ID
            result: Authorization result
            tenant_id: Tenant ID
            resource_id: Resource ID
            permission: Permission checked
            reason: Reason for result
            context: Additional context

        Returns:
            Created audit log entry
        """
        entry = AuditLogEntry(
            log_id=str(uuid4()),
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_id=resource_id,
            permission=permission,
            result=result,
            reason=reason,
            context=context or {}
        )

        # Add to logs
        self.logs.append(entry)

        # Trim if exceeds max
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]

        # Call handlers
        for handler in self.log_handlers:
            try:
                handler(entry)
            except Exception:
                pass  # Don't let handler errors break logging

        return entry

    def query_logs(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Query audit logs.

        Args:
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            action: Filter by action
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results

        Returns:
            List of matching audit log entries
        """
        results = []

        for entry in reversed(self.logs):
            if user_id and entry.user_id != user_id:
                continue
            if resource_id and entry.resource_id != resource_id:
                continue
            if action and entry.action != action:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.logs)
        authorized = sum(1 for entry in self.logs if entry.result)
        denied = total - authorized

        actions = defaultdict(int)
        for entry in self.logs:
            actions[entry.action.value] += 1

        return {
            "total_events": total,
            "authorized": authorized,
            "denied": denied,
            "actions": dict(actions)
        }


# ============================================================================
# AUTHORIZATION FSA
# ============================================================================


class AuthorizationFSA:
    """
    Authorization Finite State Automaton.

    This is a comprehensive production-ready authorization system that provides:
    - RBAC with hierarchical role support
    - ABAC with flexible policy engine
    - Resource-level granular permissions
    - Multi-tenant isolation
    - Audit logging
    - Performance caching
    - Dynamic permission management
    """

    def __init__(
        self,
        enable_caching: bool = True,
        cache_ttl: float = 300.0,
        enable_audit: bool = True,
        max_audit_entries: int = 100000
    ):
        """
        Initialize Authorization FSA.

        Args:
            enable_caching: Enable result caching
            cache_ttl: Cache time-to-live in seconds
            enable_audit: Enable audit logging
            max_audit_entries: Maximum audit log entries
        """
        self.state = AuthorizationState.UNINITIALIZED
        self.state_history: List[Tuple[AuthorizationState, datetime]] = []

        # Core components
        self.role_manager = RoleManager()
        self.permission_manager = PermissionManager()
        self.policy_engine = PolicyEngine()

        # Caching
        self.enable_caching = enable_caching
        self.cache = CacheManager(default_ttl=cache_ttl) if enable_caching else None

        # Audit logging
        self.enable_audit = enable_audit
        self.audit_logger = AuditLogger(max_entries=max_audit_entries) if enable_audit else None

        # Resources
        self.resources: Dict[str, Resource] = {}

        # State transition handlers
        self.transition_handlers: Dict[
            Tuple[AuthorizationState, AuthorizationState],
            Callable
        ] = {}

        self._transition_to(AuthorizationState.INITIALIZED)

    def _transition_to(self, new_state: AuthorizationState) -> None:
        """
        Transition to new state.

        Args:
            new_state: New state to transition to
        """
        old_state = self.state
        self.state = new_state
        self.state_history.append((new_state, datetime.utcnow()))

        # Call transition handler if exists
        handler = self.transition_handlers.get((old_state, new_state))
        if handler:
            handler()

    def register_transition_handler(
        self,
        from_state: AuthorizationState,
        to_state: AuthorizationState,
        handler: Callable
    ) -> None:
        """
        Register state transition handler.

        Args:
            from_state: Source state
            to_state: Target state
            handler: Handler function
        """
        self.transition_handlers[(from_state, to_state)] = handler

    # ========================================================================
    # ROLE MANAGEMENT
    # ========================================================================

    def create_role(
        self,
        name: str,
        permissions: Optional[Set[str]] = None,
        parent_roles: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Role:
        """
        Create a new role.

        Args:
            name: Role name
            permissions: Set of permissions
            parent_roles: List of parent role IDs
            tenant_id: Tenant ID
            description: Role description
            metadata: Additional metadata

        Returns:
            Created role
        """
        role = Role(
            role_id=str(uuid4()),
            name=name,
            description=description,
            tenant_id=tenant_id,
            permissions=permissions or set(),
            parent_roles=parent_roles or [],
            metadata=metadata or {}
        )

        self.role_manager.add_role(role)

        if self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.CREATE_ROLE,
                user_id="system",
                result=True,
                tenant_id=tenant_id,
                context={"role_id": role.role_id, "role_name": name}
            )

        return role

    def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.

        Args:
            role_id: Role ID to delete

        Returns:
            True if deleted
        """
        role = self.role_manager.get_role(role_id)
        if role:
            self.role_manager.remove_role(role_id)

            if self.enable_audit and self.audit_logger:
                self.audit_logger.log(
                    action=AuditAction.DELETE_ROLE,
                    user_id="system",
                    result=True,
                    tenant_id=role.tenant_id,
                    context={"role_id": role_id}
                )

            return True
        return False

    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Assign role to user.

        Args:
            user_id: User ID
            role_id: Role ID
            assigned_by: ID of user assigning role
            tenant_id: Tenant ID

        Returns:
            True if assigned
        """
        role = self.role_manager.get_role(role_id)
        if not role:
            return False

        self.role_manager.assign_role(user_id, role_id)

        if self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.ASSIGN_ROLE,
                user_id=assigned_by,
                result=True,
                tenant_id=tenant_id,
                context={"target_user": user_id, "role_id": role_id}
            )

        # Invalidate cache for this user
        if self.enable_caching and self.cache:
            # Clear all cache entries for this user
            self.cache.clear()

        return True

    def remove_role_from_user(
        self,
        user_id: str,
        role_id: str,
        removed_by: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Remove role from user.

        Args:
            user_id: User ID
            role_id: Role ID
            removed_by: ID of user removing role
            tenant_id: Tenant ID

        Returns:
            True if removed
        """
        self.role_manager.remove_role_from_user(user_id, role_id)

        if self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.REMOVE_ROLE,
                user_id=removed_by,
                result=True,
                tenant_id=tenant_id,
                context={"target_user": user_id, "role_id": role_id}
            )

        # Invalidate cache for this user
        if self.enable_caching and self.cache:
            self.cache.clear()

        return True

    def get_user_roles(self, user_id: str) -> List[Role]:
        """
        Get all roles for user.

        Args:
            user_id: User ID

        Returns:
            List of roles
        """
        role_ids = self.role_manager.get_user_roles(user_id)
        return [
            self.role_manager.get_role(rid)
            for rid in role_ids
            if self.role_manager.get_role(rid)
        ]

    # ========================================================================
    # PERMISSION MANAGEMENT
    # ========================================================================

    def grant_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        granted_by: str,
        tenant_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PermissionGrant:
        """
        Grant explicit permission to user.

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to grant
            granted_by: ID of user granting permission
            tenant_id: Tenant ID
            expires_at: Expiration time
            metadata: Additional metadata

        Returns:
            Permission grant
        """
        grant = self.permission_manager.grant_permission(
            user_id=user_id,
            resource_id=resource_id,
            permission=permission,
            granted_by=granted_by,
            tenant_id=tenant_id,
            expires_at=expires_at,
            metadata=metadata
        )

        if self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.GRANT_PERMISSION,
                user_id=granted_by,
                result=True,
                tenant_id=tenant_id,
                resource_id=resource_id,
                permission=permission,
                context={"target_user": user_id, "grant_id": grant.grant_id}
            )

        # Invalidate cache
        if self.enable_caching and self.cache:
            self.cache.invalidate(user_id, resource_id, permission)

        return grant

    def revoke_permission(
        self,
        grant_id: str,
        revoked_by: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Revoke permission grant.

        Args:
            grant_id: Grant ID to revoke
            revoked_by: ID of user revoking permission
            tenant_id: Tenant ID

        Returns:
            True if revoked
        """
        grant = self.permission_manager.grants.get(grant_id)
        if not grant:
            return False

        success = self.permission_manager.revoke_permission(grant_id)

        if success and self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.REVOKE_PERMISSION,
                user_id=revoked_by,
                result=True,
                tenant_id=tenant_id,
                resource_id=grant.resource_id,
                permission=grant.permission,
                context={"target_user": grant.user_id, "grant_id": grant_id}
            )

        # Invalidate cache
        if success and self.enable_caching and self.cache:
            self.cache.clear()

        return success

    # ========================================================================
    # POLICY MANAGEMENT
    # ========================================================================

    def create_policy(
        self,
        name: str,
        effect: PolicyEffect,
        resources: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        rules: Optional[List[PolicyRule]] = None,
        tenant_id: Optional[str] = None,
        priority: int = 0,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Policy:
        """
        Create authorization policy.

        Args:
            name: Policy name
            effect: Policy effect (allow/deny)
            resources: Resource types or IDs
            actions: Permissions
            rules: Policy rules
            tenant_id: Tenant ID
            priority: Policy priority
            description: Policy description
            metadata: Additional metadata

        Returns:
            Created policy
        """
        policy = Policy(
            policy_id=str(uuid4()),
            name=name,
            description=description,
            tenant_id=tenant_id,
            effect=effect,
            resources=resources or [],
            actions=actions or [],
            rules=rules or [],
            priority=priority,
            metadata=metadata or {}
        )

        self.policy_engine.add_policy(policy)

        if self.enable_audit and self.audit_logger:
            self.audit_logger.log(
                action=AuditAction.CREATE_POLICY,
                user_id="system",
                result=True,
                tenant_id=tenant_id,
                context={"policy_id": policy.policy_id, "policy_name": name}
            )

        # Invalidate cache
        if self.enable_caching and self.cache:
            self.cache.clear()

        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete policy.

        Args:
            policy_id: Policy ID to delete

        Returns:
            True if deleted
        """
        policy = self.policy_engine.get_policy(policy_id)
        if policy:
            self.policy_engine.remove_policy(policy_id)

            if self.enable_audit and self.audit_logger:
                self.audit_logger.log(
                    action=AuditAction.DELETE_POLICY,
                    user_id="system",
                    result=True,
                    tenant_id=policy.tenant_id,
                    context={"policy_id": policy_id}
                )

            # Invalidate cache
            if self.enable_caching and self.cache:
                self.cache.clear()

            return True
        return False

    # ========================================================================
    # RESOURCE MANAGEMENT
    # ========================================================================

    def register_resource(
        self,
        resource_id: str,
        resource_type: str,
        owner_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Resource:
        """
        Register resource for authorization.

        Args:
            resource_id: Resource ID
            resource_type: Resource type
            owner_id: Resource owner ID
            tenant_id: Tenant ID
            attributes: Resource attributes
            metadata: Additional metadata

        Returns:
            Registered resource
        """
        resource = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            tenant_id=tenant_id,
            owner_id=owner_id,
            attributes=attributes or {},
            metadata=metadata or {}
        )

        self.resources[resource_id] = resource
        return resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource ID

        Returns:
            Resource or None
        """
        return self.resources.get(resource_id)

    # ========================================================================
    # AUTHORIZATION
    # ========================================================================

    def authorize(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None,
        context: Optional[AuthorizationContext] = None,
        tenant_id: Optional[str] = None
    ) -> AuthorizationResult:
        """
        Authorize user action.

        This is the main authorization method that checks:
        1. Explicit permission grants
        2. Role-based permissions (RBAC)
        3. Policy-based permissions (ABAC)

        Args:
            user_id: User ID
            permission: Permission to check
            resource_id: Resource ID (optional)
            context: Authorization context
            tenant_id: Tenant ID

        Returns:
            Authorization result
        """
        start_time = time.time()

        self._transition_to(AuthorizationState.AUTHORIZING)

        # Create context if not provided
        if context is None:
            context = AuthorizationContext(
                user_id=user_id,
                tenant_id=tenant_id
            )

        # Check cache
        cached = False
        if self.enable_caching and self.cache:
            cached_result = self.cache.get(user_id, resource_id, permission, tenant_id)
            if cached_result is not None:
                cached_result.cached = True
                return cached_result

        # Get resource
        resource = None
        if resource_id:
            resource = self.get_resource(resource_id)

        authorized = False
        reason = None
        matched_policies = []
        matched_roles = []

        # Check 1: Explicit permission grants
        self._transition_to(AuthorizationState.CHECKING_PERMISSION)
        if resource_id and self.permission_manager.has_permission(user_id, resource_id, permission):
            authorized = True
            reason = "Explicit permission grant"

        # Check 2: Role-based permissions (RBAC)
        if not authorized:
            self._transition_to(AuthorizationState.VALIDATING_ROLE)
            if self.role_manager.has_permission(user_id, permission):
                authorized = True
                reason = "Role-based permission"
                user_roles = self.role_manager.get_user_roles(user_id)
                matched_roles = list(user_roles)

        # Check 3: Policy-based permissions (ABAC)
        if not authorized:
            self._transition_to(AuthorizationState.EVALUATING_POLICY)
            policy_result, policies = self.policy_engine.evaluate_policies(
                resource=resource,
                permission=permission,
                context=context,
                tenant_id=tenant_id
            )

            if policy_result:
                authorized = True
                reason = "Policy-based permission"
                matched_policies = policies

        # Resource ownership check
        if not authorized and resource and resource.owner_id == user_id:
            authorized = True
            reason = "Resource ownership"

        # Set final reason if not authorized
        if not authorized:
            reason = "No matching permissions, roles, or policies"

        # Create result
        evaluation_time = (time.time() - start_time) * 1000  # Convert to ms

        result = AuthorizationResult(
            authorized=authorized,
            user_id=user_id,
            resource_id=resource_id,
            permission=permission,
            reason=reason,
            matched_policies=matched_policies,
            matched_roles=matched_roles,
            evaluation_time_ms=evaluation_time,
            cached=cached
        )

        # Cache result
        if self.enable_caching and self.cache:
            self._transition_to(AuthorizationState.CACHING)
            self.cache.set(result, user_id, resource_id, permission, tenant_id)

        # Audit log
        if self.enable_audit and self.audit_logger:
            self._transition_to(AuthorizationState.LOGGING)
            self.audit_logger.log(
                action=AuditAction.AUTHORIZE if authorized else AuditAction.DENY,
                user_id=user_id,
                result=authorized,
                tenant_id=tenant_id,
                resource_id=resource_id,
                permission=permission,
                reason=reason,
                context={
                    "matched_policies": matched_policies,
                    "matched_roles": matched_roles,
                    "evaluation_time_ms": evaluation_time
                }
            )

        # Transition to final state
        self._transition_to(
            AuthorizationState.AUTHORIZED if authorized else AuthorizationState.UNAUTHORIZED
        )

        return result

    def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Quick permission check (returns boolean only).

        Args:
            user_id: User ID
            permission: Permission to check
            resource_id: Resource ID
            tenant_id: Tenant ID

        Returns:
            True if authorized
        """
        result = self.authorize(
            user_id=user_id,
            permission=permission,
            resource_id=resource_id,
            tenant_id=tenant_id
        )
        return result.authorized

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_state(self) -> AuthorizationState:
        """Get current FSA state."""
        return self.state

    def get_state_history(self) -> List[Tuple[AuthorizationState, datetime]]:
        """Get state transition history."""
        return self.state_history.copy()

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics."""
        if self.enable_caching and self.cache:
            return self.cache.get_stats()
        return None

    def get_audit_stats(self) -> Optional[Dict[str, Any]]:
        """Get audit statistics."""
        if self.enable_audit and self.audit_logger:
            return self.audit_logger.get_statistics()
        return None

    def clear_cache(self) -> None:
        """Clear authorization cache."""
        if self.enable_caching and self.cache:
            self.cache.clear()

    def cleanup_expired_grants(self) -> int:
        """
        Clean up expired permission grants.

        Returns:
            Number of grants removed
        """
        return self.permission_manager.cleanup_expired_grants()

    def get_user_effective_permissions(self, user_id: str) -> Set[str]:
        """
        Get all effective permissions for user.

        Args:
            user_id: User ID

        Returns:
            Set of permissions
        """
        return self.role_manager.get_effective_permissions(user_id)

    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Query audit logs.

        Args:
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            action: Filter by action
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results

        Returns:
            List of audit log entries
        """
        if self.enable_audit and self.audit_logger:
            return self.audit_logger.query_logs(
                user_id=user_id,
                resource_id=resource_id,
                action=action,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        return []

    def add_audit_handler(self, handler: Callable[[AuditLogEntry], None]) -> None:
        """
        Add custom audit log handler.

        Args:
            handler: Handler function
        """
        if self.enable_audit and self.audit_logger:
            self.audit_logger.add_handler(handler)

    def export_configuration(self) -> Dict[str, Any]:
        """
        Export authorization configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "roles": {
                role_id: {
                    "name": role.name,
                    "permissions": list(role.permissions),
                    "parent_roles": role.parent_roles,
                    "tenant_id": role.tenant_id
                }
                for role_id, role in self.role_manager.roles.items()
            },
            "policies": {
                policy_id: {
                    "name": policy.name,
                    "effect": policy.effect.value,
                    "resources": policy.resources,
                    "actions": policy.actions,
                    "priority": policy.priority,
                    "tenant_id": policy.tenant_id
                }
                for policy_id, policy in self.policy_engine.policies.items()
            },
            "user_roles": {
                user_id: list(roles)
                for user_id, roles in self.role_manager.user_roles.items()
            }
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "state": self.state.value,
            "roles": len(self.role_manager.roles),
            "policies": len(self.policy_engine.policies),
            "resources": len(self.resources),
            "grants": len(self.permission_manager.grants),
            "users_with_roles": len(self.role_manager.user_roles)
        }

        if self.enable_caching and self.cache:
            stats["cache"] = self.cache.get_stats()

        if self.enable_audit and self.audit_logger:
            stats["audit"] = self.audit_logger.get_statistics()

        return stats

"""
Authorization FSA (Finite State Automaton) for the Agno MLA Framework.

This module provides a comprehensive authorization system with:
- Role-Based Access Control (RBAC) with hierarchical roles
- Attribute-Based Access Control (ABAC) with policy engine
- Permission management (CRUD + execute)
- Resource-level authorization with granular permissions
- Policy evaluation engine with rule composition
- Integration with Authentication FSA
- Session-based and token-based authorization
- Audit logging for all authorization decisions
- Caching for performance optimization
- Dynamic permission grants/revokes
- Multi-tenant authorization support

Author: Agno Team
License: MIT
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache, wraps
from threading import Lock, RLock
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================


class PermissionType(str, Enum):
    """Permission types for resource operations."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LIST = "list"
    ADMIN = "admin"
    WILDCARD = "*"


class AuthorizationState(str, Enum):
    """FSA states for authorization flow."""

    INITIAL = "initial"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    AUTHORIZING = "authorizing"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class PolicyEffect(str, Enum):
    """Policy evaluation effects."""

    ALLOW = "allow"
    DENY = "deny"


class RoleType(str, Enum):
    """Role types in the hierarchy."""

    SYSTEM = "system"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    TEAM = "team"
    USER = "user"
    CUSTOM = "custom"


class ResourceType(str, Enum):
    """Resource types for authorization."""

    API = "api"
    DATABASE = "database"
    FILE = "file"
    SERVICE = "service"
    MODEL = "model"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class AuditAction(str, Enum):
    """Audit action types."""

    AUTHORIZATION_CHECK = "authorization_check"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    ROLE_ASSIGN = "role_assign"
    ROLE_REVOKE = "role_revoke"
    POLICY_EVALUATION = "policy_evaluation"
    ACCESS_DENIED = "access_denied"
    ACCESS_GRANTED = "access_granted"


# ============================================================================
# Exceptions
# ============================================================================


class AuthorizationError(Exception):
    """Base exception for authorization errors."""

    def __init__(self, message: str, code: str = "AUTHORIZATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class PermissionDeniedError(AuthorizationError):
    """Exception raised when permission is denied."""

    def __init__(self, message: str, required_permission: Optional[str] = None):
        self.required_permission = required_permission
        super().__init__(message, "PERMISSION_DENIED")


class InvalidRoleError(AuthorizationError):
    """Exception raised for invalid role operations."""

    def __init__(self, message: str):
        super().__init__(message, "INVALID_ROLE")


class InvalidPolicyError(AuthorizationError):
    """Exception raised for invalid policy definitions."""

    def __init__(self, message: str):
        super().__init__(message, "INVALID_POLICY")


class ResourceNotFoundError(AuthorizationError):
    """Exception raised when a resource is not found."""

    def __init__(self, message: str):
        super().__init__(message, "RESOURCE_NOT_FOUND")


class TenantIsolationError(AuthorizationError):
    """Exception raised for tenant isolation violations."""

    def __init__(self, message: str):
        super().__init__(message, "TENANT_ISOLATION_VIOLATION")


# ============================================================================
# Data Models
# ============================================================================


class Principal(BaseModel):
    """Represents an authenticated principal (user, service, etc.)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Unique identifier for the principal")
    type: str = Field(default="user", description="Type of principal (user, service, etc.)")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier for multi-tenancy")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")
    roles: List[str] = Field(default_factory=list, description="Assigned role names")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    token_id: Optional[str] = Field(default=None, description="Token identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def has_role(self, role_name: str) -> bool:
        """Check if principal has a specific role."""
        return role_name in self.roles

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a principal attribute."""
        return self.attributes.get(key, default)


class Resource(BaseModel):
    """Represents a resource to be authorized."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Unique identifier for the resource")
    type: ResourceType = Field(description="Type of resource")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    owner_id: Optional[str] = Field(default=None, description="Owner principal ID")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Resource attributes")
    tags: List[str] = Field(default_factory=list, description="Resource tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a resource attribute."""
        return self.attributes.get(key, default)

    def has_tag(self, tag: str) -> bool:
        """Check if resource has a specific tag."""
        return tag in self.tags


class Permission(BaseModel):
    """Represents a permission."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()), description="Permission ID")
    name: str = Field(description="Permission name")
    resource_type: ResourceType = Field(description="Type of resource")
    action: PermissionType = Field(description="Permitted action")
    resource_pattern: str = Field(default="*", description="Resource ID pattern (glob-style)")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Additional conditions")
    description: Optional[str] = Field(default=None, description="Permission description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time")

    def is_expired(self) -> bool:
        """Check if permission has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def matches_resource(self, resource_id: str) -> bool:
        """Check if permission matches a resource ID pattern."""
        if self.resource_pattern == "*":
            return True
        # Convert glob pattern to regex
        pattern = self.resource_pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{pattern}$", resource_id))


class Role(BaseModel):
    """Represents a role in the RBAC system."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()), description="Role ID")
    name: str = Field(description="Role name")
    type: RoleType = Field(default=RoleType.CUSTOM, description="Role type")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    parent_roles: List[str] = Field(default_factory=list, description="Parent role names")
    permissions: List[Permission] = Field(default_factory=list, description="Direct permissions")
    description: Optional[str] = Field(default=None, description="Role description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_system: bool = Field(default=False, description="Whether this is a system role")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate role name format."""
        if not v or not re.match(r"^[a-zA-Z0-9_\-\.\:]+$", v):
            raise ValueError("Role name must contain only alphanumeric, underscore, dash, dot, or colon characters")
        return v


class PolicyRule(BaseModel):
    """Represents a policy rule in ABAC."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()), description="Rule ID")
    name: str = Field(description="Rule name")
    effect: PolicyEffect = Field(description="Allow or deny effect")
    principal_conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions on principal")
    resource_conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions on resource")
    context_conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions on context")
    actions: List[PermissionType] = Field(default_factory=list, description="Actions this rule applies to")
    resource_types: List[ResourceType] = Field(default_factory=list, description="Resource types")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")
    description: Optional[str] = Field(default=None, description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class Policy(BaseModel):
    """Represents an authorization policy."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()), description="Policy ID")
    name: str = Field(description="Policy name")
    version: str = Field(default="1.0", description="Policy version")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    rules: List[PolicyRule] = Field(default_factory=list, description="Policy rules")
    default_effect: PolicyEffect = Field(default=PolicyEffect.DENY, description="Default effect")
    description: Optional[str] = Field(default=None, description="Policy description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = Field(default=True, description="Whether policy is enabled")

    def get_applicable_rules(
        self,
        action: PermissionType,
        resource_type: ResourceType,
    ) -> List[PolicyRule]:
        """Get rules applicable to an action and resource type."""
        applicable = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.actions and action not in rule.actions and PermissionType.WILDCARD not in rule.actions:
                continue
            if rule.resource_types and resource_type not in rule.resource_types:
                continue
            applicable.append(rule)
        # Sort by priority (lower number = higher priority)
        return sorted(applicable, key=lambda r: r.priority)


class AuthorizationContext(BaseModel):
    """Context for authorization decisions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    principal: Principal = Field(description="The principal requesting authorization")
    resource: Resource = Field(description="The resource being accessed")
    action: PermissionType = Field(description="The action being performed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Request ID")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.additional_context.get(key, default)


class AuthorizationDecision(BaseModel):
    """Result of an authorization decision."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    allowed: bool = Field(description="Whether access is allowed")
    principal_id: str = Field(description="Principal ID")
    resource_id: str = Field(description="Resource ID")
    action: PermissionType = Field(description="Action requested")
    reason: str = Field(description="Reason for the decision")
    matched_rules: List[str] = Field(default_factory=list, description="Matched policy rule IDs")
    matched_permissions: List[str] = Field(default_factory=list, description="Matched permission IDs")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    context: Optional[AuthorizationContext] = Field(default=None, description="Authorization context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AuditEntry(BaseModel):
    """Audit log entry for authorization events."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()), description="Audit entry ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction = Field(description="Action being audited")
    principal_id: Optional[str] = Field(default=None, description="Principal ID")
    resource_id: Optional[str] = Field(default=None, description="Resource ID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    decision: Optional[bool] = Field(default=None, description="Authorization decision")
    reason: Optional[str] = Field(default=None, description="Reason for action")
    ip_address: Optional[str] = Field(default=None, description="Client IP")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Caching System
# ============================================================================


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    value: Any
    created_at: float
    ttl: float
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl


class AuthorizationCache:
    """Thread-safe cache for authorization decisions with TTL support."""

    def __init__(self, default_ttl: float = 300.0, max_size: int = 10000):
        """
        Initialize the authorization cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args: Any) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, *key_parts: Any) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            *key_parts: Parts to construct the cache key

        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(*key_parts)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            entry.hits += 1
            self._hits += 1
            return entry.value

    def set(self, value: Any, *key_parts: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.

        Args:
            value: Value to cache
            *key_parts: Parts to construct the cache key
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        key = self._make_key(*key_parts)
        ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            # Evict oldest entries if cache is full
            if len(self._cache) >= self._max_size:
                # Remove 10% of oldest entries
                num_to_remove = max(1, self._max_size // 10)
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].created_at,
                )
                for old_key, _ in sorted_entries[:num_to_remove]:
                    del self._cache[old_key]

            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl,
            )

    def invalidate(self, *key_parts: Any) -> None:
        """
        Invalidate a cache entry.

        Args:
            *key_parts: Parts to construct the cache key
        """
        key = self._make_key(*key_parts)
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }


# ============================================================================
# Condition Evaluator
# ============================================================================


class ConditionEvaluator:
    """Evaluates conditions in policy rules."""

    @staticmethod
    def evaluate(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate conditions against context.

        Supports operators:
        - eq: equals
        - ne: not equals
        - in: value in list
        - not_in: value not in list
        - gt: greater than
        - gte: greater than or equal
        - lt: less than
        - lte: less than or equal
        - contains: string contains
        - matches: regex match
        - exists: key exists in context

        Args:
            conditions: Dictionary of conditions
            context: Context to evaluate against

        Returns:
            True if all conditions are met, False otherwise
        """
        if not conditions:
            return True

        for key, condition in conditions.items():
            if not ConditionEvaluator._evaluate_single(key, condition, context):
                return False

        return True

    @staticmethod
    def _evaluate_single(key: str, condition: Any, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        # Handle nested keys (e.g., "attributes.department")
        value = ConditionEvaluator._get_nested_value(context, key)

        # If condition is a dict, it contains operators
        if isinstance(condition, dict):
            for operator, expected in condition.items():
                if not ConditionEvaluator._apply_operator(operator, value, expected):
                    return False
            return True
        else:
            # Direct equality check
            return value == condition

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], key: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value

    @staticmethod
    def _apply_operator(operator: str, value: Any, expected: Any) -> bool:
        """Apply a comparison operator."""
        if operator == "eq":
            return value == expected
        elif operator == "ne":
            return value != expected
        elif operator == "in":
            return value in expected if expected else False
        elif operator == "not_in":
            return value not in expected if expected else True
        elif operator == "gt":
            return value > expected if value is not None else False
        elif operator == "gte":
            return value >= expected if value is not None else False
        elif operator == "lt":
            return value < expected if value is not None else False
        elif operator == "lte":
            return value <= expected if value is not None else False
        elif operator == "contains":
            return expected in str(value) if value is not None else False
        elif operator == "matches":
            return bool(re.match(expected, str(value))) if value is not None else False
        elif operator == "exists":
            return (value is not None) == expected
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False


# ============================================================================
# Policy Engine
# ============================================================================


class PolicyEngine:
    """ABAC policy evaluation engine."""

    def __init__(self):
        """Initialize the policy engine."""
        self._policies: Dict[str, Policy] = {}
        self._lock = RLock()
        self._evaluator = ConditionEvaluator()

    def add_policy(self, policy: Policy) -> None:
        """
        Add a policy to the engine.

        Args:
            policy: Policy to add
        """
        with self._lock:
            self._policies[policy.id] = policy
            logger.info(f"Added policy: {policy.name} (ID: {policy.id})")

    def remove_policy(self, policy_id: str) -> None:
        """
        Remove a policy from the engine.

        Args:
            policy_id: ID of policy to remove
        """
        with self._lock:
            if policy_id in self._policies:
                policy = self._policies.pop(policy_id)
                logger.info(f"Removed policy: {policy.name} (ID: {policy_id})")

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get a policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy if found, None otherwise
        """
        with self._lock:
            return self._policies.get(policy_id)

    def list_policies(self, tenant_id: Optional[str] = None) -> List[Policy]:
        """
        List all policies, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant ID filter

        Returns:
            List of policies
        """
        with self._lock:
            policies = list(self._policies.values())
            if tenant_id is not None:
                policies = [p for p in policies if p.tenant_id == tenant_id]
            return policies

    def evaluate(self, context: AuthorizationContext) -> Tuple[bool, List[str], str]:
        """
        Evaluate policies for an authorization context.

        Args:
            context: Authorization context

        Returns:
            Tuple of (allowed, matched_rule_ids, reason)
        """
        with self._lock:
            # Get applicable policies
            applicable_policies = [
                p
                for p in self._policies.values()
                if p.enabled
                and (p.tenant_id is None or p.tenant_id == context.principal.tenant_id)
            ]

            if not applicable_policies:
                return False, [], "No applicable policies found"

            # Collect all applicable rules from all policies
            all_rules: List[Tuple[PolicyRule, Policy]] = []
            for policy in applicable_policies:
                rules = policy.get_applicable_rules(context.action, context.resource.type)
                for rule in rules:
                    all_rules.append((rule, policy))

            # Sort by priority
            all_rules.sort(key=lambda x: x[0].priority)

            # Evaluate rules in priority order
            matched_rules = []
            for rule, policy in all_rules:
                if self._evaluate_rule(rule, context):
                    matched_rules.append(rule.id)
                    if rule.effect == PolicyEffect.DENY:
                        return False, matched_rules, f"Denied by policy rule: {rule.name}"
                    elif rule.effect == PolicyEffect.ALLOW:
                        return True, matched_rules, f"Allowed by policy rule: {rule.name}"

            # No rules matched, use default effect from first policy
            default_effect = applicable_policies[0].default_effect
            if default_effect == PolicyEffect.ALLOW:
                return True, [], "Allowed by default policy effect"
            else:
                return False, [], "Denied by default policy effect"

    def _evaluate_rule(self, rule: PolicyRule, context: AuthorizationContext) -> bool:
        """
        Evaluate a single policy rule.

        Args:
            rule: Policy rule to evaluate
            context: Authorization context

        Returns:
            True if rule conditions are met, False otherwise
        """
        # Build evaluation contexts
        principal_context = {
            "id": context.principal.id,
            "type": context.principal.type,
            "tenant_id": context.principal.tenant_id,
            "roles": context.principal.roles,
            **context.principal.attributes,
        }

        resource_context = {
            "id": context.resource.id,
            "type": context.resource.type.value,
            "tenant_id": context.resource.tenant_id,
            "owner_id": context.resource.owner_id,
            "tags": context.resource.tags,
            **context.resource.attributes,
        }

        context_data = {
            "timestamp": context.timestamp.isoformat(),
            "ip_address": context.ip_address,
            "user_agent": context.user_agent,
            **context.additional_context,
        }

        # Evaluate all conditions
        if not self._evaluator.evaluate(rule.principal_conditions, principal_context):
            return False

        if not self._evaluator.evaluate(rule.resource_conditions, resource_context):
            return False

        if not self._evaluator.evaluate(rule.context_conditions, context_data):
            return False

        return True


# ============================================================================
# Role Manager
# ============================================================================


class RoleManager:
    """Manages roles and role hierarchy."""

    def __init__(self):
        """Initialize the role manager."""
        self._roles: Dict[str, Role] = {}
        self._role_hierarchy: Dict[str, Set[str]] = defaultdict(set)  # role -> inherited roles
        self._lock = RLock()
        self._initialize_system_roles()

    def _initialize_system_roles(self) -> None:
        """Initialize default system roles."""
        system_admin = Role(
            name="system:admin",
            type=RoleType.SYSTEM,
            description="System administrator with full access",
            is_system=True,
            permissions=[
                Permission(
                    name="system:admin:all",
                    resource_type=ResourceType.CUSTOM,
                    action=PermissionType.WILDCARD,
                    resource_pattern="*",
                )
            ],
        )

        system_user = Role(
            name="system:user",
            type=RoleType.SYSTEM,
            description="Standard system user",
            is_system=True,
            permissions=[
                Permission(
                    name="system:user:read",
                    resource_type=ResourceType.CUSTOM,
                    action=PermissionType.READ,
                    resource_pattern="*",
                )
            ],
        )

        self.add_role(system_admin)
        self.add_role(system_user)

    def add_role(self, role: Role) -> None:
        """
        Add a role to the manager.

        Args:
            role: Role to add

        Raises:
            InvalidRoleError: If role already exists
        """
        with self._lock:
            if role.name in self._roles:
                raise InvalidRoleError(f"Role already exists: {role.name}")

            self._roles[role.name] = role
            self._update_hierarchy(role)
            logger.info(f"Added role: {role.name}")

    def remove_role(self, role_name: str) -> None:
        """
        Remove a role.

        Args:
            role_name: Name of role to remove

        Raises:
            InvalidRoleError: If role is a system role or doesn't exist
        """
        with self._lock:
            role = self._roles.get(role_name)
            if role is None:
                raise InvalidRoleError(f"Role not found: {role_name}")
            if role.is_system:
                raise InvalidRoleError(f"Cannot remove system role: {role_name}")

            del self._roles[role_name]
            del self._role_hierarchy[role_name]
            logger.info(f"Removed role: {role_name}")

    def get_role(self, role_name: str) -> Optional[Role]:
        """
        Get a role by name.

        Args:
            role_name: Role name

        Returns:
            Role if found, None otherwise
        """
        with self._lock:
            return self._roles.get(role_name)

    def list_roles(self, tenant_id: Optional[str] = None) -> List[Role]:
        """
        List all roles, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant ID filter

        Returns:
            List of roles
        """
        with self._lock:
            roles = list(self._roles.values())
            if tenant_id is not None:
                roles = [r for r in roles if r.tenant_id == tenant_id]
            return roles

    def _update_hierarchy(self, role: Role) -> None:
        """
        Update role hierarchy when a role is added/modified.

        Args:
            role: Role to update hierarchy for
        """
        inherited = set()
        for parent_name in role.parent_roles:
            inherited.add(parent_name)
            # Recursively add parent's inherited roles
            inherited.update(self._role_hierarchy.get(parent_name, set()))

        self._role_hierarchy[role.name] = inherited

    def get_effective_roles(self, role_names: List[str]) -> Set[str]:
        """
        Get all effective roles including inherited roles.

        Args:
            role_names: List of direct role names

        Returns:
            Set of all effective role names (direct + inherited)
        """
        with self._lock:
            effective = set(role_names)
            for role_name in role_names:
                effective.update(self._role_hierarchy.get(role_name, set()))
            return effective

    def get_effective_permissions(self, role_names: List[str]) -> List[Permission]:
        """
        Get all effective permissions from roles.

        Args:
            role_names: List of role names

        Returns:
            List of all permissions (direct + inherited)
        """
        with self._lock:
            effective_roles = self.get_effective_roles(role_names)
            permissions = []

            for role_name in effective_roles:
                role = self._roles.get(role_name)
                if role:
                    permissions.extend(role.permissions)

            return permissions

    def add_permission_to_role(
        self,
        role_name: str,
        permission: Permission,
    ) -> None:
        """
        Add a permission to a role.

        Args:
            role_name: Role name
            permission: Permission to add

        Raises:
            InvalidRoleError: If role doesn't exist or is a system role
        """
        with self._lock:
            role = self._roles.get(role_name)
            if role is None:
                raise InvalidRoleError(f"Role not found: {role_name}")
            if role.is_system:
                raise InvalidRoleError(f"Cannot modify system role: {role_name}")

            role.permissions.append(permission)
            logger.info(f"Added permission {permission.name} to role {role_name}")

    def remove_permission_from_role(
        self,
        role_name: str,
        permission_id: str,
    ) -> None:
        """
        Remove a permission from a role.

        Args:
            role_name: Role name
            permission_id: Permission ID to remove

        Raises:
            InvalidRoleError: If role doesn't exist or is a system role
        """
        with self._lock:
            role = self._roles.get(role_name)
            if role is None:
                raise InvalidRoleError(f"Role not found: {role_name}")
            if role.is_system:
                raise InvalidRoleError(f"Cannot modify system role: {role_name}")

            role.permissions = [p for p in role.permissions if p.id != permission_id]
            logger.info(f"Removed permission {permission_id} from role {role_name}")


# ============================================================================
# Audit Logger
# ============================================================================


class AuditLogger:
    """Audit logger for authorization events."""

    def __init__(self, max_entries: int = 100000):
        """
        Initialize audit logger.

        Args:
            max_entries: Maximum number of entries to keep in memory
        """
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries
        self._lock = Lock()

    def log(
        self,
        action: AuditAction,
        principal_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        decision: Optional[bool] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an audit entry.

        Args:
            action: Audit action type
            principal_id: Optional principal ID
            resource_id: Optional resource ID
            tenant_id: Optional tenant ID
            decision: Optional authorization decision
            reason: Optional reason
            ip_address: Optional client IP
            metadata: Optional additional metadata
        """
        entry = AuditEntry(
            action=action,
            principal_id=principal_id,
            resource_id=resource_id,
            tenant_id=tenant_id,
            decision=decision,
            reason=reason,
            ip_address=ip_address,
            metadata=metadata or {},
        )

        with self._lock:
            self._entries.append(entry)

            # Trim old entries if needed
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]

        logger.debug(f"Audit log: {action.value} - {reason}")

    def get_entries(
        self,
        principal_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Get audit entries with optional filters.

        Args:
            principal_id: Filter by principal ID
            resource_id: Filter by resource ID
            tenant_id: Filter by tenant ID
            action: Filter by action type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of entries to return

        Returns:
            List of matching audit entries
        """
        with self._lock:
            entries = self._entries

            # Apply filters
            if principal_id is not None:
                entries = [e for e in entries if e.principal_id == principal_id]
            if resource_id is not None:
                entries = [e for e in entries if e.resource_id == resource_id]
            if tenant_id is not None:
                entries = [e for e in entries if e.tenant_id == tenant_id]
            if action is not None:
                entries = [e for e in entries if e.action == action]
            if start_time is not None:
                entries = [e for e in entries if e.timestamp >= start_time]
            if end_time is not None:
                entries = [e for e in entries if e.timestamp <= end_time]

            # Return most recent entries up to limit
            return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all audit entries."""
        with self._lock:
            self._entries.clear()
            logger.info("Cleared all audit entries")


# ============================================================================
# Authorization FSA
# ============================================================================


class AuthorizationFSA:
    """
    Authorization Finite State Automaton.

    This is the main class that provides comprehensive authorization capabilities
    including RBAC, ABAC, caching, auditing, and multi-tenancy support.
    """

    def __init__(
        self,
        cache_ttl: float = 300.0,
        cache_enabled: bool = True,
        audit_enabled: bool = True,
    ):
        """
        Initialize the Authorization FSA.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            cache_enabled: Whether to enable caching
            audit_enabled: Whether to enable audit logging
        """
        self._state = AuthorizationState.INITIAL
        self._lock = RLock()

        # Components
        self._role_manager = RoleManager()
        self._policy_engine = PolicyEngine()
        self._cache = AuthorizationCache(default_ttl=cache_ttl) if cache_enabled else None
        self._audit_logger = AuditLogger() if audit_enabled else None

        # Principal-role assignments
        self._principal_roles: Dict[str, Set[str]] = defaultdict(set)

        # Direct principal permissions (for dynamic grants)
        self._principal_permissions: Dict[str, List[Permission]] = defaultdict(list)

        # Session tracking
        self._sessions: Dict[str, Principal] = {}
        self._token_principals: Dict[str, Principal] = {}

        logger.info("AuthorizationFSA initialized")

    @property
    def state(self) -> AuthorizationState:
        """Get current FSA state."""
        return self._state

    def transition_to(self, new_state: AuthorizationState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: New state to transition to
        """
        with self._lock:
            old_state = self._state
            self._state = new_state
            logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    # ========================================================================
    # Principal Management
    # ========================================================================

    def register_session(self, principal: Principal) -> str:
        """
        Register a session for a principal.

        Args:
            principal: Principal to register

        Returns:
            Session ID
        """
        with self._lock:
            if principal.session_id is None:
                principal.session_id = str(uuid4())

            self._sessions[principal.session_id] = principal

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.AUTHORIZATION_CHECK,
                    principal_id=principal.id,
                    tenant_id=principal.tenant_id,
                    reason="Session registered",
                )

            logger.info(f"Registered session for principal: {principal.id}")
            return principal.session_id

    def get_principal_from_session(self, session_id: str) -> Optional[Principal]:
        """
        Get principal from session ID.

        Args:
            session_id: Session identifier

        Returns:
            Principal if found, None otherwise
        """
        with self._lock:
            return self._sessions.get(session_id)

    def register_token(self, principal: Principal, token_id: str) -> None:
        """
        Register a token for a principal.

        Args:
            principal: Principal to register
            token_id: Token identifier
        """
        with self._lock:
            principal.token_id = token_id
            self._token_principals[token_id] = principal

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.AUTHORIZATION_CHECK,
                    principal_id=principal.id,
                    tenant_id=principal.tenant_id,
                    reason="Token registered",
                )

            logger.info(f"Registered token for principal: {principal.id}")

    def get_principal_from_token(self, token_id: str) -> Optional[Principal]:
        """
        Get principal from token ID.

        Args:
            token_id: Token identifier

        Returns:
            Principal if found, None otherwise
        """
        with self._lock:
            return self._token_principals.get(token_id)

    def revoke_session(self, session_id: str) -> None:
        """
        Revoke a session.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            principal = self._sessions.pop(session_id, None)
            if principal and self._cache:
                # Invalidate related cache entries
                self._invalidate_principal_cache(principal.id)

            if self._audit_logger and principal:
                self._audit_logger.log(
                    action=AuditAction.AUTHORIZATION_CHECK,
                    principal_id=principal.id,
                    tenant_id=principal.tenant_id,
                    reason="Session revoked",
                )

            logger.info(f"Revoked session: {session_id}")

    def revoke_token(self, token_id: str) -> None:
        """
        Revoke a token.

        Args:
            token_id: Token identifier
        """
        with self._lock:
            principal = self._token_principals.pop(token_id, None)
            if principal and self._cache:
                # Invalidate related cache entries
                self._invalidate_principal_cache(principal.id)

            if self._audit_logger and principal:
                self._audit_logger.log(
                    action=AuditAction.AUTHORIZATION_CHECK,
                    principal_id=principal.id,
                    tenant_id=principal.tenant_id,
                    reason="Token revoked",
                )

            logger.info(f"Revoked token: {token_id}")

    # ========================================================================
    # Role Management
    # ========================================================================

    def create_role(self, role: Role) -> None:
        """
        Create a new role.

        Args:
            role: Role to create
        """
        with self._lock:
            self._role_manager.add_role(role)

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.ROLE_ASSIGN,
                    tenant_id=role.tenant_id,
                    reason=f"Role created: {role.name}",
                )

    def delete_role(self, role_name: str) -> None:
        """
        Delete a role.

        Args:
            role_name: Name of role to delete
        """
        with self._lock:
            role = self._role_manager.get_role(role_name)
            self._role_manager.remove_role(role_name)

            if self._cache:
                self._cache.clear()  # Clear all cache as roles may affect many principals

            if self._audit_logger and role:
                self._audit_logger.log(
                    action=AuditAction.ROLE_REVOKE,
                    tenant_id=role.tenant_id,
                    reason=f"Role deleted: {role_name}",
                )

    def assign_role(self, principal_id: str, role_name: str) -> None:
        """
        Assign a role to a principal.

        Args:
            principal_id: Principal identifier
            role_name: Role name

        Raises:
            InvalidRoleError: If role doesn't exist
        """
        with self._lock:
            role = self._role_manager.get_role(role_name)
            if role is None:
                raise InvalidRoleError(f"Role not found: {role_name}")

            self._principal_roles[principal_id].add(role_name)

            if self._cache:
                self._invalidate_principal_cache(principal_id)

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.ROLE_ASSIGN,
                    principal_id=principal_id,
                    tenant_id=role.tenant_id,
                    reason=f"Role assigned: {role_name}",
                )

            logger.info(f"Assigned role {role_name} to principal {principal_id}")

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        """
        Revoke a role from a principal.

        Args:
            principal_id: Principal identifier
            role_name: Role name
        """
        with self._lock:
            self._principal_roles[principal_id].discard(role_name)

            if self._cache:
                self._invalidate_principal_cache(principal_id)

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.ROLE_REVOKE,
                    principal_id=principal_id,
                    reason=f"Role revoked: {role_name}",
                )

            logger.info(f"Revoked role {role_name} from principal {principal_id}")

    def get_principal_roles(self, principal_id: str) -> List[str]:
        """
        Get all roles assigned to a principal.

        Args:
            principal_id: Principal identifier

        Returns:
            List of role names
        """
        with self._lock:
            return list(self._principal_roles.get(principal_id, set()))

    # ========================================================================
    # Permission Management
    # ========================================================================

    def grant_permission(
        self,
        principal_id: str,
        permission: Permission,
    ) -> None:
        """
        Grant a direct permission to a principal.

        Args:
            principal_id: Principal identifier
            permission: Permission to grant
        """
        with self._lock:
            self._principal_permissions[principal_id].append(permission)

            if self._cache:
                self._invalidate_principal_cache(principal_id)

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.PERMISSION_GRANT,
                    principal_id=principal_id,
                    tenant_id=permission.tenant_id,
                    reason=f"Permission granted: {permission.name}",
                )

            logger.info(f"Granted permission {permission.name} to principal {principal_id}")

    def revoke_permission(
        self,
        principal_id: str,
        permission_id: str,
    ) -> None:
        """
        Revoke a direct permission from a principal.

        Args:
            principal_id: Principal identifier
            permission_id: Permission ID to revoke
        """
        with self._lock:
            permissions = self._principal_permissions.get(principal_id, [])
            self._principal_permissions[principal_id] = [
                p for p in permissions if p.id != permission_id
            ]

            if self._cache:
                self._invalidate_principal_cache(principal_id)

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.PERMISSION_REVOKE,
                    principal_id=principal_id,
                    reason=f"Permission revoked: {permission_id}",
                )

            logger.info(f"Revoked permission {permission_id} from principal {principal_id}")

    def get_effective_permissions(self, principal: Principal) -> List[Permission]:
        """
        Get all effective permissions for a principal (from roles + direct grants).

        Args:
            principal: Principal

        Returns:
            List of effective permissions
        """
        with self._lock:
            # Get permissions from roles
            all_roles = list(self._principal_roles.get(principal.id, set()))
            all_roles.extend(principal.roles)  # Include roles from principal object
            role_permissions = self._role_manager.get_effective_permissions(all_roles)

            # Get direct permissions
            direct_permissions = self._principal_permissions.get(principal.id, [])

            # Combine and filter expired permissions
            all_permissions = role_permissions + direct_permissions
            active_permissions = [p for p in all_permissions if not p.is_expired()]

            return active_permissions

    # ========================================================================
    # Policy Management
    # ========================================================================

    def add_policy(self, policy: Policy) -> None:
        """
        Add an authorization policy.

        Args:
            policy: Policy to add
        """
        with self._lock:
            self._policy_engine.add_policy(policy)

            if self._cache:
                self._cache.clear()  # Clear cache as policy may affect many authorizations

            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.POLICY_EVALUATION,
                    tenant_id=policy.tenant_id,
                    reason=f"Policy added: {policy.name}",
                )

    def remove_policy(self, policy_id: str) -> None:
        """
        Remove an authorization policy.

        Args:
            policy_id: Policy ID to remove
        """
        with self._lock:
            policy = self._policy_engine.get_policy(policy_id)
            self._policy_engine.remove_policy(policy_id)

            if self._cache:
                self._cache.clear()  # Clear cache as policy may affect many authorizations

            if self._audit_logger and policy:
                self._audit_logger.log(
                    action=AuditAction.POLICY_EVALUATION,
                    tenant_id=policy.tenant_id,
                    reason=f"Policy removed: {policy.name}",
                )

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get a policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy if found, None otherwise
        """
        return self._policy_engine.get_policy(policy_id)

    def list_policies(self, tenant_id: Optional[str] = None) -> List[Policy]:
        """
        List all policies.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of policies
        """
        return self._policy_engine.list_policies(tenant_id)

    # ========================================================================
    # Authorization
    # ========================================================================

    def authorize(
        self,
        principal: Principal,
        resource: Resource,
        action: PermissionType,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationDecision:
        """
        Authorize a principal's access to a resource.

        This is the main authorization method that combines RBAC and ABAC.

        Args:
            principal: Principal requesting access
            resource: Resource being accessed
            action: Action being performed
            context: Optional additional context

        Returns:
            AuthorizationDecision with the result

        Raises:
            TenantIsolationError: If tenant isolation is violated
        """
        with self._lock:
            self.transition_to(AuthorizationState.AUTHORIZING)

            # Check cache first
            if self._cache:
                cached = self._cache.get(principal.id, resource.id, action.value)
                if cached is not None:
                    logger.debug(f"Cache hit for authorization check")
                    return cached

            # Build authorization context
            auth_context = AuthorizationContext(
                principal=principal,
                resource=resource,
                action=action,
                additional_context=context or {},
            )

            # Tenant isolation check
            if not self._check_tenant_isolation(principal, resource):
                self.transition_to(AuthorizationState.DENIED)
                decision = AuthorizationDecision(
                    allowed=False,
                    principal_id=principal.id,
                    resource_id=resource.id,
                    action=action,
                    reason="Tenant isolation violation",
                    context=auth_context,
                )

                if self._audit_logger:
                    self._audit_logger.log(
                        action=AuditAction.ACCESS_DENIED,
                        principal_id=principal.id,
                        resource_id=resource.id,
                        tenant_id=principal.tenant_id,
                        decision=False,
                        reason=decision.reason,
                    )

                return decision

            # Check RBAC permissions
            rbac_allowed, rbac_permissions = self._check_rbac(principal, resource, action)

            # Check ABAC policies
            abac_allowed, matched_rules, abac_reason = self._policy_engine.evaluate(auth_context)

            # Combine RBAC and ABAC results (either can grant access)
            allowed = rbac_allowed or abac_allowed

            # Build reason
            if allowed:
                reason_parts = []
                if rbac_allowed:
                    reason_parts.append(f"RBAC: {len(rbac_permissions)} permission(s) matched")
                if abac_allowed:
                    reason_parts.append(f"ABAC: {abac_reason}")
                reason = "; ".join(reason_parts)
            else:
                reason = "No matching permissions or policies"

            # Create decision
            decision = AuthorizationDecision(
                allowed=allowed,
                principal_id=principal.id,
                resource_id=resource.id,
                action=action,
                reason=reason,
                matched_rules=matched_rules,
                matched_permissions=[p.id for p in rbac_permissions],
                context=auth_context,
            )

            # Cache the decision
            if self._cache:
                self._cache.set(decision, principal.id, resource.id, action.value)

            # Audit log
            if self._audit_logger:
                self._audit_logger.log(
                    action=AuditAction.ACCESS_GRANTED if allowed else AuditAction.ACCESS_DENIED,
                    principal_id=principal.id,
                    resource_id=resource.id,
                    tenant_id=principal.tenant_id,
                    decision=allowed,
                    reason=reason,
                )

            # Update state
            if allowed:
                self.transition_to(AuthorizationState.AUTHORIZED)
            else:
                self.transition_to(AuthorizationState.DENIED)

            return decision

    def _check_rbac(
        self,
        principal: Principal,
        resource: Resource,
        action: PermissionType,
    ) -> Tuple[bool, List[Permission]]:
        """
        Check RBAC permissions.

        Args:
            principal: Principal
            resource: Resource
            action: Action

        Returns:
            Tuple of (allowed, matched_permissions)
        """
        permissions = self.get_effective_permissions(principal)
        matched = []

        for permission in permissions:
            # Check if permission applies to this resource type
            if permission.resource_type != resource.type and permission.resource_type != ResourceType.CUSTOM:
                continue

            # Check if permission allows this action
            if permission.action != action and permission.action != PermissionType.WILDCARD:
                continue

            # Check if permission matches resource ID
            if not permission.matches_resource(resource.id):
                continue

            # Check tenant
            if permission.tenant_id and permission.tenant_id != resource.tenant_id:
                continue

            matched.append(permission)

        return len(matched) > 0, matched

    def _check_tenant_isolation(self, principal: Principal, resource: Resource) -> bool:
        """
        Check tenant isolation.

        Args:
            principal: Principal
            resource: Resource

        Returns:
            True if tenant isolation is satisfied, False otherwise
        """
        # If resource has no tenant, it's globally accessible
        if resource.tenant_id is None:
            return True

        # If principal has no tenant, deny access to tenant resources
        if principal.tenant_id is None:
            return False

        # Principal must belong to same tenant
        return principal.tenant_id == resource.tenant_id

    def _invalidate_principal_cache(self, principal_id: str) -> None:
        """
        Invalidate all cache entries for a principal.

        Args:
            principal_id: Principal ID
        """
        if self._cache:
            # Note: This is a simplified implementation
            # In production, you'd want a more sophisticated cache invalidation strategy
            self._cache.clear()

    def check_permission(
        self,
        principal: Principal,
        resource: Resource,
        action: PermissionType,
        raise_on_deny: bool = False,
    ) -> bool:
        """
        Check if a principal has permission for an action.

        Args:
            principal: Principal
            resource: Resource
            action: Action
            raise_on_deny: Whether to raise exception on denial

        Returns:
            True if allowed, False otherwise

        Raises:
            PermissionDeniedError: If raise_on_deny is True and permission is denied
        """
        decision = self.authorize(principal, resource, action)

        if not decision.allowed and raise_on_deny:
            raise PermissionDeniedError(
                decision.reason,
                required_permission=f"{resource.type.value}:{action.value}",
            )

        return decision.allowed

    def require_permission(
        self,
        resource: Resource,
        action: PermissionType,
    ) -> Callable:
        """
        Decorator to require permission for a function.

        Args:
            resource: Resource
            action: Action

        Returns:
            Decorator function

        Example:
            @auth_fsa.require_permission(resource, PermissionType.READ)
            def read_data(principal: Principal):
                ...
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # First argument should be principal
                if not args or not isinstance(args[0], Principal):
                    raise AuthorizationError("First argument must be Principal")

                principal = args[0]
                self.check_permission(principal, resource, action, raise_on_deny=True)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache stats
        """
        if self._cache:
            return self._cache.get_stats()
        return {"enabled": False}

    def clear_cache(self) -> None:
        """Clear authorization cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Cleared authorization cache")

    def get_audit_logs(
        self,
        principal_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Get audit logs.

        Args:
            principal_id: Optional principal filter
            resource_id: Optional resource filter
            tenant_id: Optional tenant filter
            action: Optional action filter
            limit: Maximum entries to return

        Returns:
            List of audit entries
        """
        if self._audit_logger:
            return self._audit_logger.get_entries(
                principal_id=principal_id,
                resource_id=resource_id,
                tenant_id=tenant_id,
                action=action,
                limit=limit,
            )
        return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Dictionary of statistics
        """
        with self._lock:
            return {
                "state": self._state.value,
                "principals": {
                    "sessions": len(self._sessions),
                    "tokens": len(self._token_principals),
                    "with_roles": len(self._principal_roles),
                    "with_permissions": len(self._principal_permissions),
                },
                "roles": len(self._role_manager.list_roles()),
                "policies": len(self._policy_engine.list_policies()),
                "cache": self.get_cache_stats(),
            }


# ============================================================================
# Helper Functions
# ============================================================================


def create_default_authorization_fsa() -> AuthorizationFSA:
    """
    Create an AuthorizationFSA instance with default configuration.

    Returns:
        Configured AuthorizationFSA instance
    """
    return AuthorizationFSA(
        cache_ttl=300.0,  # 5 minutes
        cache_enabled=True,
        audit_enabled=True,
    )


__all__ = [
    # Main FSA
    "AuthorizationFSA",
    # Enums
    "PermissionType",
    "AuthorizationState",
    "PolicyEffect",
    "RoleType",
    "ResourceType",
    "AuditAction",
    # Models
    "Principal",
    "Resource",
    "Permission",
    "Role",
    "Policy",
    "PolicyRule",
    "AuthorizationContext",
    "AuthorizationDecision",
    "AuditEntry",
    # Exceptions
    "AuthorizationError",
    "PermissionDeniedError",
    "InvalidRoleError",
    "InvalidPolicyError",
    "ResourceNotFoundError",
    "TenantIsolationError",
    # Components
    "RoleManager",
    "PolicyEngine",
    "AuthorizationCache",
    "AuditLogger",
    "ConditionEvaluator",
    # Helpers
    "create_default_authorization_fsa",
]

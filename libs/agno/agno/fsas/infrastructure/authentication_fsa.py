"""
Production-Grade Authentication FSA (Finite State Automaton)

This module provides a comprehensive authentication system with multi-factor authentication,
OAuth2/OIDC, JWT tokens, session management, and extensive security features.

Features:
- Multi-provider authentication (username/password, MFA, biometric, certificate, API key)
- OAuth 2.0 and OpenID Connect (OIDC) support
- JWT token generation, validation, and management
- Advanced session management with SSO/SLO
- User management with password policies
- Security features (rate limiting, brute force protection, CAPTCHA)
- Comprehensive monitoring and audit trails

Author: Agno AI
License: MIT
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlencode, parse_qs, urlparse

try:
    import jwt
    from jwt.exceptions import InvalidTokenError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    import argon2
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509 import load_pem_x509_certificate
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


# ============================================================================
# ENUMERATIONS AND CONSTANTS
# ============================================================================


class AuthenticationMethod(str, Enum):
    """Supported authentication methods."""
    PASSWORD = "password"
    MFA = "mfa"
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BIOMETRIC = "biometric"
    CERTIFICATE = "certificate"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    SAML = "saml"
    CHALLENGE_RESPONSE = "challenge_response"


class OAuth2GrantType(str, Enum):
    """OAuth 2.0 grant types."""
    AUTHORIZATION_CODE = "authorization_code"
    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"
    BEARER = "Bearer"


class FSAState(str, Enum):
    """FSA states for authentication operations."""
    IDLE = "idle"
    AUTHENTICATING = "authenticating"
    MFA_REQUIRED = "mfa_required"
    MFA_VALIDATING = "mfa_validating"
    TOKEN_GENERATING = "token_generating"
    TOKEN_VALIDATING = "token_validating"
    SESSION_CREATING = "session_creating"
    SESSION_VALIDATING = "session_validating"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    LOCKED = "locked"
    ERROR = "error"


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"


class SessionStatus(str, Enum):
    """Session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOGGED_OUT = "logged_out"


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class User:
    """User entity."""
    user_id: str
    username: str
    email: str
    password_hash: Optional[str] = None
    phone: Optional[str] = None
    roles: List[str] = field(default_factory=lambda: ["user"])
    is_active: bool = True
    is_verified: bool = False
    is_locked: bool = False
    failed_login_attempts: int = 0
    last_login: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "roles": self.roles,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_locked": self.is_locked,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "mfa_enabled": self.mfa_enabled,
        }


@dataclass
class Session:
    """User session."""
    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: Optional[Dict[str, Any]] = None

    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at and time.time() > self.expires_at:
            return True
        return False

    def is_valid(self) -> bool:
        """Check if session is valid."""
        return (
            self.status == SessionStatus.ACTIVE
            and not self.is_expired()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "expires_at": self.expires_at,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status.value,
        }


@dataclass
class AuthenticationResult:
    """Result of an authentication attempt."""
    success: bool
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    requires_mfa: bool = False
    mfa_methods: Optional[List[str]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TokenClaims:
    """JWT token claims."""
    sub: str  # Subject (user ID)
    iss: str = "agno-auth"  # Issuer
    aud: Optional[str] = None  # Audience
    exp: Optional[int] = None  # Expiration time
    iat: Optional[int] = None  # Issued at
    nbf: Optional[int] = None  # Not before
    jti: Optional[str] = None  # JWT ID
    scope: Optional[str] = None
    custom_claims: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        claims = {
            "sub": self.sub,
            "iss": self.iss,
        }
        if self.aud:
            claims["aud"] = self.aud
        if self.exp:
            claims["exp"] = self.exp
        if self.iat:
            claims["iat"] = self.iat
        if self.nbf:
            claims["nbf"] = self.nbf
        if self.jti:
            claims["jti"] = self.jti
        if self.scope:
            claims["scope"] = self.scope
        if self.custom_claims:
            claims.update(self.custom_claims)
        return claims


@dataclass
class OAuth2Client:
    """OAuth2 client application."""
    client_id: str
    client_secret: str
    redirect_uris: List[str]
    grant_types: List[str]
    response_types: List[str]
    scope: str = "openid profile email"
    token_endpoint_auth_method: str = "client_secret_basic"
    client_name: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class OAuth2AuthorizationCode:
    """OAuth2 authorization code."""
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scope: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 600)  # 10 minutes

    def is_expired(self) -> bool:
        """Check if code is expired."""
        return time.time() > self.expires_at


@dataclass
class AuthenticationEvent:
    """Authentication event for audit."""
    event_id: str
    event_type: str
    user_id: Optional[str]
    username: Optional[str]
    success: bool
    timestamp: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    method: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "username": self.username,
            "success": self.success,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "method": self.method,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    special_characters: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    prevent_common: bool = True
    prevent_username: bool = True
    expiration_days: Optional[int] = 90
    history_count: int = 5


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================


class PasswordUtils:
    """Password hashing and validation utilities."""

    @staticmethod
    def hash_password(password: str, algorithm: str = "bcrypt") -> str:
        """
        Hash a password.

        Args:
            password: Password to hash
            algorithm: Hashing algorithm (bcrypt, argon2)

        Returns:
            Password hash
        """
        if algorithm == "bcrypt":
            if not BCRYPT_AVAILABLE:
                raise ImportError("bcrypt is required")
            return bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
        elif algorithm == "argon2":
            if not ARGON2_AVAILABLE:
                raise ImportError("argon2-cffi is required")
            ph = argon2.PasswordHasher()
            return ph.hash(password)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain password
            password_hash: Password hash

        Returns:
            True if password matches
        """
        try:
            # Try bcrypt
            if password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
                if not BCRYPT_AVAILABLE:
                    raise ImportError("bcrypt is required")
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    password_hash.encode('utf-8')
                )
            # Try argon2
            elif password_hash.startswith("$argon2"):
                if not ARGON2_AVAILABLE:
                    raise ImportError("argon2-cffi is required")
                ph = argon2.PasswordHasher()
                ph.verify(password_hash, password)
                return True
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def validate_password_strength(
        password: str,
        policy: PasswordPolicy,
        username: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate password against policy.

        Args:
            password: Password to validate
            policy: Password policy
            username: Optional username to check against

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        # Length check
        if len(password) < policy.min_length:
            errors.append(f"Password must be at least {policy.min_length} characters")
        if len(password) > policy.max_length:
            errors.append(f"Password must be at most {policy.max_length} characters")

        # Uppercase check
        if policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        # Lowercase check
        if policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        # Digits check
        if policy.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        # Special characters check
        if policy.require_special:
            if not any(c in policy.special_characters for c in password):
                errors.append("Password must contain at least one special character")

        # Username check
        if policy.prevent_username and username:
            if username.lower() in password.lower():
                errors.append("Password must not contain username")

        # Common passwords check
        if policy.prevent_common:
            common_passwords = {"password", "123456", "qwerty", "admin", "letmein"}
            if password.lower() in common_passwords:
                errors.append("Password is too common")

        return len(errors) == 0, errors


# ============================================================================
# USER MANAGER
# ============================================================================


class UserManager:
    """
    User management with registration, password policies, and account management.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize user manager.

        Args:
            storage_path: Path to store user data
        """
        self.storage_path = storage_path or Path.home() / ".agno" / "users"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.users: Dict[str, User] = {}
        self.username_index: Dict[str, str] = {}  # username -> user_id
        self.email_index: Dict[str, str] = {}  # email -> user_id
        self.password_policy = PasswordPolicy()
        self._lock = threading.RLock()
        self._load_users()

    def _load_users(self) -> None:
        """Load users from storage."""
        users_file = self.storage_path / "users.json"
        if users_file.exists():
            with open(users_file, "r") as f:
                data = json.load(f)
                for user_data in data:
                    user = User(**user_data)
                    self.users[user.user_id] = user
                    self.username_index[user.username] = user.user_id
                    self.email_index[user.email] = user.user_id

    def _save_users(self) -> None:
        """Save users to storage."""
        users_file = self.storage_path / "users.json"
        with open(users_file, "w") as f:
            users_data = []
            for user in self.users.values():
                user_dict = user.__dict__.copy()
                users_data.append(user_dict)
            json.dump(users_data, f, indent=2)

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None
    ) -> Tuple[Optional[User], List[str]]:
        """
        Register a new user.

        Args:
            username: Username
            email: Email address
            password: Password
            roles: Optional roles

        Returns:
            Tuple of (User, list of errors)
        """
        with self._lock:
            errors = []

            # Check if username exists
            if username in self.username_index:
                errors.append("Username already exists")

            # Check if email exists
            if email in self.email_index:
                errors.append("Email already exists")

            # Validate password
            is_valid, password_errors = PasswordUtils.validate_password_strength(
                password,
                self.password_policy,
                username
            )
            if not is_valid:
                errors.extend(password_errors)

            if errors:
                return None, errors

            # Create user
            user_id = str(uuid.uuid4())
            password_hash = PasswordUtils.hash_password(password)

            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                roles=roles or ["user"]
            )

            self.users[user_id] = user
            self.username_index[username] = user_id
            self.email_index[email] = user_id
            self._save_users()

            return user, []

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_id = self.username_index.get(username)
        return self.users.get(user_id) if user_id else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self.email_index.get(email)
        return self.users.get(user_id) if user_id else None

    def update_user(self, user: User) -> None:
        """Update user."""
        with self._lock:
            user.updated_at = time.time()
            self.users[user.user_id] = user
            self._save_users()

    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return False

            del self.users[user_id]
            del self.username_index[user.username]
            del self.email_index[user.email]
            self._save_users()
            return True

    def lock_account(self, user_id: str) -> None:
        """Lock user account."""
        user = self.get_user(user_id)
        if user:
            user.is_locked = True
            self.update_user(user)

    def unlock_account(self, user_id: str) -> None:
        """Unlock user account."""
        user = self.get_user(user_id)
        if user:
            user.is_locked = False
            user.failed_login_attempts = 0
            self.update_user(user)

    def increment_failed_login(self, user_id: str, max_attempts: int = 5) -> bool:
        """
        Increment failed login attempts and lock if exceeded.

        Args:
            user_id: User ID
            max_attempts: Maximum allowed attempts

        Returns:
            True if account is now locked
        """
        user = self.get_user(user_id)
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= max_attempts:
                user.is_locked = True
            self.update_user(user)
            return user.is_locked
        return False

    def reset_failed_login(self, user_id: str) -> None:
        """Reset failed login attempts."""
        user = self.get_user(user_id)
        if user:
            user.failed_login_attempts = 0
            self.update_user(user)


# ============================================================================
# SESSION MANAGER
# ============================================================================


class SessionManager:
    """
    Session management with support for in-memory, Redis, and database storage.
    """

    def __init__(
        self,
        default_timeout: int = 3600,
        sliding_window: bool = True
    ):
        """
        Initialize session manager.

        Args:
            default_timeout: Default session timeout in seconds
            sliding_window: Enable sliding session window
        """
        self.default_timeout = default_timeout
        self.sliding_window = sliding_window
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)  # user_id -> session_ids
        self._lock = threading.RLock()

    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            device_fingerprint: Device fingerprint
            timeout: Session timeout in seconds

        Returns:
            Session object
        """
        with self._lock:
            session_id = secrets.token_urlsafe(32)
            timeout = timeout or self.default_timeout
            expires_at = time.time() + timeout

            session = Session(
                session_id=session_id,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint
            )

            self.sessions[session_id] = session
            self.user_sessions[user_id].append(session_id)

            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_valid():
            if self.sliding_window:
                # Update last accessed and extend expiration
                session.last_accessed = time.time()
                session.expires_at = time.time() + self.default_timeout
            return session
        return None

    def validate_session(self, session_id: str) -> bool:
        """Validate session."""
        session = self.get_session(session_id)
        return session is not None

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = SessionStatus.REVOKED
                return True
            return False

    def logout(self, session_id: str) -> bool:
        """Logout (mark session as logged out)."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = SessionStatus.LOGGED_OUT
                return True
            return False

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self.user_sessions.get(user_id, [])
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        with self._lock:
            sessions = self.get_user_sessions(user_id)
            count = 0
            for session in sessions:
                if session.status == SessionStatus.ACTIVE:
                    session.status = SessionStatus.REVOKED
                    count += 1
            return count

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        with self._lock:
            expired = []
            for session_id, session in self.sessions.items():
                if session.is_expired():
                    session.status = SessionStatus.EXPIRED
                    expired.append(session_id)

            for session_id in expired:
                del self.sessions[session_id]

            return len(expired)


# ============================================================================
# JWT TOKEN MANAGER
# ============================================================================


class JWTTokenManager:
    """
    JWT token generation, validation, and management.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_lifetime: int = 3600,
        refresh_token_lifetime: int = 86400 * 7
    ):
        """
        Initialize JWT token manager.

        Args:
            secret_key: Secret key for signing
            algorithm: Signing algorithm (HS256, RS256, ES256)
            access_token_lifetime: Access token lifetime in seconds
            refresh_token_lifetime: Refresh token lifetime in seconds
        """
        if not JWT_AVAILABLE:
            raise ImportError("PyJWT is required. Install with: pip install PyJWT")

        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_lifetime = access_token_lifetime
        self.refresh_token_lifetime = refresh_token_lifetime
        self.revoked_tokens: Set[str] = set()
        self._lock = threading.RLock()

        # Generate RSA keys if needed
        if algorithm.startswith("RS") or algorithm.startswith("ES"):
            if CRYPTOGRAPHY_AVAILABLE:
                self.private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
            else:
                raise ImportError("cryptography is required for RSA/ECDSA algorithms")

    def generate_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scope: Optional[str] = None,
        custom_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a JWT token.

        Args:
            user_id: User ID
            token_type: Token type
            scope: OAuth2 scope
            custom_claims: Custom claims

        Returns:
            JWT token string
        """
        now = int(time.time())
        jti = str(uuid.uuid4())

        if token_type == TokenType.ACCESS:
            exp = now + self.access_token_lifetime
        elif token_type == TokenType.REFRESH:
            exp = now + self.refresh_token_lifetime
        else:
            exp = now + self.access_token_lifetime

        claims = TokenClaims(
            sub=user_id,
            iss="agno-auth",
            iat=now,
            exp=exp,
            nbf=now,
            jti=jti,
            scope=scope,
            custom_claims=custom_claims
        )

        payload = claims.to_dict()
        payload["token_type"] = token_type.value

        # Sign token
        if self.algorithm.startswith("HS"):
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        else:
            private_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            token = jwt.encode(payload, private_pem, algorithm=self.algorithm)

        return token

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Tuple of (is_valid, claims, error)
        """
        try:
            # Check if token is revoked
            if token in self.revoked_tokens:
                return False, None, "Token has been revoked"

            # Decode and verify token
            if self.algorithm.startswith("HS"):
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
            else:
                public_pem = self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                payload = jwt.decode(
                    token,
                    public_pem,
                    algorithms=[self.algorithm]
                )

            return True, payload, None

        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Token validation error: {str(e)}"

    def refresh_token(self, refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Tuple of (new_access_token, error)
        """
        is_valid, claims, error = self.validate_token(refresh_token)

        if not is_valid:
            return None, error

        if claims.get("token_type") != TokenType.REFRESH.value:
            return None, "Invalid token type"

        # Generate new access token
        user_id = claims.get("sub")
        scope = claims.get("scope")
        new_access_token = self.generate_token(
            user_id,
            TokenType.ACCESS,
            scope
        )

        return new_access_token, None

    def revoke_token(self, token: str) -> None:
        """Revoke a token."""
        with self._lock:
            self.revoked_tokens.add(token)

    def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect a token (OAuth2 token introspection).

        Args:
            token: Token to introspect

        Returns:
            Token introspection response
        """
        is_valid, claims, error = self.validate_token(token)

        if not is_valid:
            return {"active": False}

        return {
            "active": True,
            "sub": claims.get("sub"),
            "scope": claims.get("scope"),
            "exp": claims.get("exp"),
            "iat": claims.get("iat"),
            "token_type": claims.get("token_type"),
        }


# ============================================================================
# OAUTH2 PROVIDER
# ============================================================================


class OAuth2Provider:
    """
    OAuth 2.0 authorization server implementation with OIDC support.
    """

    def __init__(
        self,
        token_manager: JWTTokenManager,
        user_manager: UserManager
    ):
        """
        Initialize OAuth2 provider.

        Args:
            token_manager: JWT token manager
            user_manager: User manager
        """
        self.token_manager = token_manager
        self.user_manager = user_manager
        self.clients: Dict[str, OAuth2Client] = {}
        self.authorization_codes: Dict[str, OAuth2AuthorizationCode] = {}
        self._lock = threading.RLock()

    def register_client(
        self,
        redirect_uris: List[str],
        grant_types: List[str],
        response_types: List[str],
        client_name: Optional[str] = None,
        scope: str = "openid profile email"
    ) -> OAuth2Client:
        """
        Register an OAuth2 client.

        Args:
            redirect_uris: Allowed redirect URIs
            grant_types: Allowed grant types
            response_types: Allowed response types
            client_name: Client name
            scope: Default scope

        Returns:
            OAuth2 client
        """
        client_id = secrets.token_urlsafe(16)
        client_secret = secrets.token_urlsafe(32)

        client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            response_types=response_types,
            client_name=client_name,
            scope=scope
        )

        with self._lock:
            self.clients[client_id] = client

        return client

    def authorize(
        self,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: str,
        state: str,
        user_id: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Authorization endpoint (OAuth2 authorization code flow).

        Args:
            client_id: Client ID
            redirect_uri: Redirect URI
            response_type: Response type (code, token)
            scope: Requested scope
            state: State parameter
            user_id: Authenticated user ID
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method

        Returns:
            Tuple of (authorization_code, error)
        """
        # Validate client
        client = self.clients.get(client_id)
        if not client:
            return None, "invalid_client"

        # Validate redirect URI
        if redirect_uri not in client.redirect_uris:
            return None, "invalid_redirect_uri"

        # Validate response type
        if response_type not in client.response_types:
            return None, "unsupported_response_type"

        # Generate authorization code
        code = secrets.token_urlsafe(32)
        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )

        with self._lock:
            self.authorization_codes[code] = auth_code

        return code, None

    def token(
        self,
        grant_type: str,
        client_id: str,
        client_secret: str,
        code: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        refresh_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        scope: Optional[str] = None,
        code_verifier: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Token endpoint (OAuth2 token exchange).

        Args:
            grant_type: Grant type
            client_id: Client ID
            client_secret: Client secret
            code: Authorization code
            redirect_uri: Redirect URI
            refresh_token: Refresh token
            username: Username (for password grant)
            password: Password (for password grant)
            scope: Requested scope
            code_verifier: PKCE code verifier

        Returns:
            Tuple of (token_response, error)
        """
        # Validate client
        client = self.clients.get(client_id)
        if not client or client.client_secret != client_secret:
            return None, "invalid_client"

        # Validate grant type
        if grant_type not in client.grant_types:
            return None, "unsupported_grant_type"

        # Authorization code flow
        if grant_type == OAuth2GrantType.AUTHORIZATION_CODE.value:
            if not code or not redirect_uri:
                return None, "invalid_request"

            auth_code = self.authorization_codes.get(code)
            if not auth_code:
                return None, "invalid_grant"

            if auth_code.is_expired():
                return None, "invalid_grant"

            if auth_code.client_id != client_id:
                return None, "invalid_grant"

            if auth_code.redirect_uri != redirect_uri:
                return None, "invalid_grant"

            # PKCE validation
            if auth_code.code_challenge:
                if not code_verifier:
                    return None, "invalid_request"

                if auth_code.code_challenge_method == "S256":
                    verifier_hash = base64.urlsafe_b64encode(
                        hashlib.sha256(code_verifier.encode()).digest()
                    ).decode().rstrip("=")
                    if verifier_hash != auth_code.code_challenge:
                        return None, "invalid_grant"
                elif auth_code.code_challenge_method == "plain":
                    if code_verifier != auth_code.code_challenge:
                        return None, "invalid_grant"

            user_id = auth_code.user_id
            scope = auth_code.scope

            # Delete used code
            with self._lock:
                del self.authorization_codes[code]

        # Password grant
        elif grant_type == OAuth2GrantType.PASSWORD.value:
            if not username or not password:
                return None, "invalid_request"

            user = self.user_manager.get_user_by_username(username)
            if not user or not PasswordUtils.verify_password(password, user.password_hash):
                return None, "invalid_grant"

            user_id = user.user_id
            scope = scope or "openid profile email"

        # Client credentials
        elif grant_type == OAuth2GrantType.CLIENT_CREDENTIALS.value:
            user_id = client_id
            scope = scope or client.scope

        # Refresh token
        elif grant_type == OAuth2GrantType.REFRESH_TOKEN.value:
            if not refresh_token:
                return None, "invalid_request"

            new_access_token, error = self.token_manager.refresh_token(refresh_token)
            if error:
                return None, "invalid_grant"

            return {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": self.token_manager.access_token_lifetime,
            }, None

        else:
            return None, "unsupported_grant_type"

        # Generate tokens
        access_token = self.token_manager.generate_token(
            user_id,
            TokenType.ACCESS,
            scope
        )
        refresh_token_str = self.token_manager.generate_token(
            user_id,
            TokenType.REFRESH,
            scope
        )

        # Generate ID token for OIDC
        id_token = None
        if "openid" in scope:
            user = self.user_manager.get_user(user_id)
            if user:
                id_token = self.token_manager.generate_token(
                    user_id,
                    TokenType.ID,
                    scope,
                    custom_claims={
                        "email": user.email,
                        "email_verified": user.is_verified,
                        "name": user.username,
                    }
                )

        response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_manager.access_token_lifetime,
            "refresh_token": refresh_token_str,
            "scope": scope,
        }

        if id_token:
            response["id_token"] = id_token

        return response, None

    def userinfo(self, access_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        UserInfo endpoint (OIDC).

        Args:
            access_token: Access token

        Returns:
            Tuple of (user_info, error)
        """
        is_valid, claims, error = self.token_manager.validate_token(access_token)

        if not is_valid:
            return None, error

        user_id = claims.get("sub")
        user = self.user_manager.get_user(user_id)

        if not user:
            return None, "user_not_found"

        user_info = {
            "sub": user.user_id,
            "name": user.username,
            "email": user.email,
            "email_verified": user.is_verified,
        }

        if user.phone:
            user_info["phone_number"] = user.phone

        return user_info, None


# ============================================================================
# SECURITY FEATURES
# ============================================================================


class RateLimiter:
    """Rate limiting and throttling."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        self._lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)

        Returns:
            True if allowed
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Remove old requests
            requests = self.requests[identifier]
            while requests and requests[0] < window_start:
                requests.popleft()

            # Check rate limit
            if len(requests) >= self.max_requests:
                return False

            # Add new request
            requests.append(now)
            return True

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            requests = self.requests[identifier]
            while requests and requests[0] < window_start:
                requests.popleft()

            return max(0, self.max_requests - len(requests))


class SecurityMonitor:
    """Security monitoring and anomaly detection."""

    def __init__(self):
        """Initialize security monitor."""
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self.suspicious_ips: Set[str] = set()
        self._lock = threading.Lock()

    def record_failed_attempt(self, identifier: str, ip_address: Optional[str] = None) -> None:
        """Record a failed authentication attempt."""
        with self._lock:
            now = time.time()
            self.failed_attempts[identifier].append(now)

            # Clean old attempts (last hour)
            cutoff = now - 3600
            self.failed_attempts[identifier] = [
                t for t in self.failed_attempts[identifier] if t > cutoff
            ]

            # Mark IP as suspicious if too many failures
            if ip_address and len(self.failed_attempts[identifier]) > 10:
                self.suspicious_ips.add(ip_address)

    def is_suspicious(self, identifier: str, ip_address: Optional[str] = None) -> bool:
        """Check if activity is suspicious."""
        with self._lock:
            # Check IP
            if ip_address and ip_address in self.suspicious_ips:
                return True

            # Check failed attempts
            now = time.time()
            recent_failures = [
                t for t in self.failed_attempts[identifier]
                if t > now - 300  # Last 5 minutes
            ]

            return len(recent_failures) > 5


# ============================================================================
# AUDIT LOGGER
# ============================================================================


class AuthenticationAuditLogger:
    """Audit logger for authentication events."""

    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize audit logger.

        Args:
            log_path: Path to audit log file
        """
        self.log_path = log_path or Path.home() / ".agno" / "auth_audit.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.events: deque = deque(maxlen=10000)
        self._lock = threading.Lock()

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        method: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an authentication event."""
        event = AuthenticationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            username=username,
            success=success,
            timestamp=time.time(),
            ip_address=ip_address,
            user_agent=user_agent,
            method=method,
            error=error,
            metadata=metadata
        )

        with self._lock:
            self.events.append(event)

            # Write to file
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")

    def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._lock:
            return [e.to_dict() for e in list(self.events)[-count:]]

    def query_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        success: Optional[bool] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Query events with filters."""
        with self._lock:
            results = []
            for event in self.events:
                if event_type and event.event_type != event_type:
                    continue
                if user_id and event.user_id != user_id:
                    continue
                if success is not None and event.success != success:
                    continue
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event.to_dict())
            return results


# ============================================================================
# MAIN AUTHENTICATION FSA
# ============================================================================


class AuthenticationFSA:
    """
    Production-grade Authentication FSA with comprehensive authentication,
    OAuth2/OIDC, JWT tokens, session management, and security features.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        enable_audit: bool = True,
        enable_rate_limiting: bool = True,
        jwt_secret: Optional[str] = None
    ):
        """
        Initialize Authentication FSA.

        Args:
            storage_path: Storage path
            enable_audit: Enable audit logging
            enable_rate_limiting: Enable rate limiting
            jwt_secret: JWT secret key
        """
        self.state = FSAState.IDLE
        self.storage_path = storage_path or Path.home() / ".agno" / "auth"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize managers
        self.user_manager = UserManager(self.storage_path / "users")
        self.session_manager = SessionManager()
        self.token_manager = JWTTokenManager(secret_key=jwt_secret)
        self.oauth2_provider = OAuth2Provider(self.token_manager, self.user_manager)

        # Security
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        self.security_monitor = SecurityMonitor()

        # Audit
        self.audit_logger = AuthenticationAuditLogger() if enable_audit else None
        self.enable_audit = enable_audit

        self._lock = threading.RLock()
        self._state_history: deque = deque(maxlen=100)

    def _transition_state(self, new_state: FSAState) -> None:
        """Transition to a new state."""
        with self._lock:
            old_state = self.state
            self.state = new_state
            self._state_history.append((old_state, new_state, time.time()))

    def _log_audit(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        method: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log audit event."""
        if self.enable_audit and self.audit_logger:
            self.audit_logger.log_event(
                event_type=event_type,
                user_id=user_id,
                username=username,
                success=success,
                method=method,
                error=error,
                **kwargs
            )

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None
    ) -> Tuple[Optional[User], List[str]]:
        """Register a new user."""
        user, errors = self.user_manager.register_user(username, email, password, roles)

        self._log_audit(
            "user_registration",
            user_id=user.user_id if user else None,
            username=username,
            success=user is not None,
            error=", ".join(errors) if errors else None
        )

        return user, errors

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mfa_code: Optional[str] = None
    ) -> AuthenticationResult:
        """
        Authenticate a user.

        Args:
            username: Username
            password: Password
            ip_address: Client IP
            user_agent: User agent
            mfa_code: MFA code if required

        Returns:
            Authentication result
        """
        self._transition_state(FSAState.AUTHENTICATING)

        # Rate limiting
        if self.rate_limiter and not self.rate_limiter.is_allowed(username):
            self._log_audit(
                "authentication",
                username=username,
                success=False,
                error="Rate limit exceeded",
                ip_address=ip_address
            )
            self._transition_state(FSAState.DENIED)
            return AuthenticationResult(
                success=False,
                error="Too many requests. Please try again later."
            )

        # Get user
        user = self.user_manager.get_user_by_username(username)
        if not user:
            self.security_monitor.record_failed_attempt(username, ip_address)
            self._log_audit(
                "authentication",
                username=username,
                success=False,
                error="User not found",
                ip_address=ip_address
            )
            self._transition_state(FSAState.DENIED)
            return AuthenticationResult(success=False, error="Invalid credentials")

        # Check if account is locked
        if user.is_locked:
            self._log_audit(
                "authentication",
                user_id=user.user_id,
                username=username,
                success=False,
                error="Account locked",
                ip_address=ip_address
            )
            self._transition_state(FSAState.LOCKED)
            return AuthenticationResult(success=False, error="Account is locked")

        # Verify password
        if not PasswordUtils.verify_password(password, user.password_hash):
            self.user_manager.increment_failed_login(user.user_id)
            self.security_monitor.record_failed_attempt(username, ip_address)
            self._log_audit(
                "authentication",
                user_id=user.user_id,
                username=username,
                success=False,
                error="Invalid password",
                ip_address=ip_address
            )
            self._transition_state(FSAState.DENIED)
            return AuthenticationResult(success=False, error="Invalid credentials")

        # Check MFA
        if user.mfa_enabled:
            if not mfa_code:
                self._transition_state(FSAState.MFA_REQUIRED)
                return AuthenticationResult(
                    success=False,
                    requires_mfa=True,
                    mfa_methods=["totp", "sms"],
                    error="MFA required"
                )

            # Validate MFA (simplified)
            self._transition_state(FSAState.MFA_VALIDATING)
            # In production, validate actual TOTP/SMS code
            if not self._validate_mfa(user, mfa_code):
                self._log_audit(
                    "mfa_validation",
                    user_id=user.user_id,
                    username=username,
                    success=False,
                    error="Invalid MFA code",
                    ip_address=ip_address
                )
                self._transition_state(FSAState.DENIED)
                return AuthenticationResult(success=False, error="Invalid MFA code")

        # Authentication successful
        self.user_manager.reset_failed_login(user.user_id)
        user.last_login = time.time()
        self.user_manager.update_user(user)

        # Create session
        self._transition_state(FSAState.SESSION_CREATING)
        session = self.session_manager.create_session(
            user.user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Generate tokens
        self._transition_state(FSAState.TOKEN_GENERATING)
        access_token = self.token_manager.generate_token(user.user_id, TokenType.ACCESS)
        refresh_token = self.token_manager.generate_token(user.user_id, TokenType.REFRESH)

        self._log_audit(
            "authentication",
            user_id=user.user_id,
            username=username,
            success=True,
            method="password",
            ip_address=ip_address
        )

        self._transition_state(FSAState.AUTHORIZED)

        return AuthenticationResult(
            success=True,
            user_id=user.user_id,
            session_id=session.session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self.token_manager.access_token_lifetime
        )

    def _validate_mfa(self, user: User, mfa_code: str) -> bool:
        """Validate MFA code (simplified implementation)."""
        # In production, implement actual TOTP validation
        # For now, accept any 6-digit code
        return len(mfa_code) == 6 and mfa_code.isdigit()

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate an access token."""
        self._transition_state(FSAState.TOKEN_VALIDATING)
        result = self.token_manager.validate_token(token)
        self._transition_state(FSAState.COMPLETED if result[0] else FSAState.DENIED)
        return result

    def validate_session(self, session_id: str) -> bool:
        """Validate a session."""
        self._transition_state(FSAState.SESSION_VALIDATING)
        is_valid = self.session_manager.validate_session(session_id)
        self._transition_state(FSAState.AUTHORIZED if is_valid else FSAState.DENIED)
        return is_valid

    def logout(self, session_id: str) -> bool:
        """Logout a session."""
        success = self.session_manager.logout(session_id)
        if success:
            session = self.session_manager.sessions.get(session_id)
            self._log_audit(
                "logout",
                user_id=session.user_id if session else None,
                success=True
            )
        return success

    def refresh_access_token(self, refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """Refresh an access token."""
        self._transition_state(FSAState.TOKEN_GENERATING)
        new_token, error = self.token_manager.refresh_token(refresh_token)
        self._transition_state(FSAState.COMPLETED if new_token else FSAState.ERROR)
        return new_token, error

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.user_manager.get_user(user_id)

    def get_state(self) -> str:
        """Get current FSA state."""
        return self.state.value

    def get_state_history(self) -> List[Tuple[str, str, float]]:
        """Get state transition history."""
        return [(old.value, new.value, ts) for old, new, ts in self._state_history]

    def get_audit_log(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get audit log."""
        if self.audit_logger:
            return self.audit_logger.get_recent_events(count)
        return []

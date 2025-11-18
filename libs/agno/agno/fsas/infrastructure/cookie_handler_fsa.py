"""
Cookie Handler FSA for the Agno MLA Framework

This module provides a comprehensive Finite State Automaton (FSA) for managing HTTP cookies
with enterprise-grade security, GDPR compliance, and integration with session management.

Features:
- Secure cookie creation, reading, updating, and deletion (CRUD)
- Cookie encryption and signing for tamper protection
- Session cookie vs persistent cookie management
- Cookie expiration and max-age handling
- Domain and path scope management
- Cookie jar management for multiple domains
- GDPR compliance features with consent tracking
- Cookie attributes validation
- Integration with Session Manager FSA

Author: Agno Framework Team
License: MIT
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from agno.utils.log import logger


class CookieState(Enum):
    """FSA states for cookie lifecycle management."""
    UNINITIALIZED = "uninitialized"
    CREATED = "created"
    VALIDATED = "validated"
    ENCRYPTED = "encrypted"
    SIGNED = "signed"
    STORED = "stored"
    RETRIEVED = "retrieved"
    EXPIRED = "expired"
    DELETED = "deleted"
    INVALID = "invalid"


class SameSitePolicy(Enum):
    """SameSite cookie attribute values."""
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


class CookieScope(Enum):
    """Cookie scope types."""
    SESSION = "session"
    PERSISTENT = "persistent"
    FLASH = "flash"  # Single request cookie


class ConsentType(Enum):
    """GDPR cookie consent types."""
    STRICTLY_NECESSARY = "strictly_necessary"
    FUNCTIONAL = "functional"
    ANALYTICS = "analytics"
    ADVERTISING = "advertising"
    SOCIAL_MEDIA = "social_media"


@dataclass
class CookieAttributes:
    """
    Comprehensive cookie attributes with security and compliance features.

    Attributes:
        name: Cookie name (must be valid)
        value: Cookie value
        domain: Cookie domain scope
        path: Cookie path scope
        expires: Expiration timestamp (None for session cookies)
        max_age: Maximum age in seconds
        secure: HTTPS only flag
        http_only: JavaScript access prevention flag
        same_site: SameSite policy
        scope: Cookie scope type
        consent_type: GDPR consent category
        encrypted: Whether cookie is encrypted
        signed: Whether cookie is signed
        priority: Cookie priority (low, medium, high)
        partition_key: Cookie partitioning key
    """
    name: str
    value: str
    domain: Optional[str] = None
    path: str = "/"
    expires: Optional[datetime] = None
    max_age: Optional[int] = None
    secure: bool = True
    http_only: bool = True
    same_site: SameSitePolicy = SameSitePolicy.LAX
    scope: CookieScope = CookieScope.SESSION
    consent_type: ConsentType = ConsentType.STRICTLY_NECESSARY
    encrypted: bool = False
    signed: bool = False
    priority: str = "medium"
    partition_key: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert cookie attributes to dictionary."""
        data = asdict(self)
        data['same_site'] = self.same_site.value
        data['scope'] = self.scope.value
        data['consent_type'] = self.consent_type.value
        data['created_at'] = self.created_at.isoformat()
        data['last_accessed'] = self.last_accessed.isoformat()
        if self.expires:
            data['expires'] = self.expires.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CookieAttributes':
        """Create cookie attributes from dictionary."""
        data = data.copy()
        data['same_site'] = SameSitePolicy(data['same_site'])
        data['scope'] = CookieScope(data['scope'])
        data['consent_type'] = ConsentType(data['consent_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        if data.get('expires'):
            data['expires'] = datetime.fromisoformat(data['expires'])
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if cookie has expired."""
        if self.expires is None:
            return False
        return datetime.now(timezone.utc) > self.expires

    def is_secure_enough(self) -> bool:
        """Check if cookie meets minimum security requirements."""
        return self.secure and self.http_only

    def matches_domain(self, domain: str) -> bool:
        """Check if cookie matches given domain."""
        if not self.domain:
            return True
        cookie_domain = self.domain.lower()
        target_domain = domain.lower()
        if cookie_domain.startswith('.'):
            return target_domain.endswith(cookie_domain) or target_domain == cookie_domain[1:]
        return cookie_domain == target_domain

    def matches_path(self, path: str) -> bool:
        """Check if cookie matches given path."""
        return path.startswith(self.path)


@dataclass
class ConsentRecord:
    """
    GDPR consent tracking record.

    Attributes:
        user_id: User identifier
        consent_types: Set of consented cookie types
        timestamp: When consent was given
        ip_address: User's IP address
        user_agent: User's browser user agent
        expires_at: When consent expires
        version: Consent policy version
    """
    user_id: str
    consent_types: Set[ConsentType]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: Optional[datetime] = None
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert consent record to dictionary."""
        return {
            'user_id': self.user_id,
            'consent_types': [ct.value for ct in self.consent_types],
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'version': self.version,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentRecord':
        """Create consent record from dictionary."""
        data = data.copy()
        data['consent_types'] = {ConsentType(ct) for ct in data['consent_types']}
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)

    def has_consent(self, consent_type: ConsentType) -> bool:
        """Check if user has given consent for specific type."""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return consent_type in self.consent_types

    def is_expired(self) -> bool:
        """Check if consent has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class CookieValidator:
    """Validator for cookie names, values, and attributes."""

    # RFC 6265 compliant patterns
    COOKIE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9!#$%&\'*+\-.^_`|~]+$')
    COOKIE_VALUE_PATTERN = re.compile(r'^[a-zA-Z0-9!#$%&\'()*+\-./:<=>?@[\]^_`{|}~\s]*$')
    DOMAIN_PATTERN = re.compile(r'^\.?[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
    PATH_PATTERN = re.compile(r'^/[^\x00-\x1F\x7F;]*$')

    # Security constraints
    MAX_NAME_LENGTH = 256
    MAX_VALUE_LENGTH = 4096
    MAX_COOKIES_PER_DOMAIN = 50
    MAX_TOTAL_COOKIES = 3000

    @classmethod
    def validate_name(cls, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate cookie name.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Cookie name cannot be empty"
        if len(name) > cls.MAX_NAME_LENGTH:
            return False, f"Cookie name exceeds maximum length of {cls.MAX_NAME_LENGTH}"
        if not cls.COOKIE_NAME_PATTERN.match(name):
            return False, "Cookie name contains invalid characters"
        if name.lower().startswith('__secure-') or name.lower().startswith('__host-'):
            # These prefixes have special requirements
            return True, None
        return True, None

    @classmethod
    def validate_value(cls, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate cookie value.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(value) > cls.MAX_VALUE_LENGTH:
            return False, f"Cookie value exceeds maximum length of {cls.MAX_VALUE_LENGTH}"
        if not cls.COOKIE_VALUE_PATTERN.match(value):
            return False, "Cookie value contains invalid characters"
        return True, None

    @classmethod
    def validate_domain(cls, domain: str) -> Tuple[bool, Optional[str]]:
        """
        Validate cookie domain.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not domain:
            return True, None  # Domain is optional
        if not cls.DOMAIN_PATTERN.match(domain):
            return False, "Invalid domain format"
        if domain.count('.') < 1 and not domain.startswith('.'):
            return False, "Domain must contain at least one dot or start with a dot"
        return True, None

    @classmethod
    def validate_path(cls, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate cookie path.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return False, "Path cannot be empty"
        if not path.startswith('/'):
            return False, "Path must start with '/'"
        if not cls.PATH_PATTERN.match(path):
            return False, "Path contains invalid characters"
        return True, None

    @classmethod
    def validate_secure_prefix(cls, name: str, attributes: CookieAttributes) -> Tuple[bool, Optional[str]]:
        """
        Validate __Secure- and __Host- prefixes.

        Returns:
            Tuple of (is_valid, error_message)
        """
        name_lower = name.lower()
        if name_lower.startswith('__secure-'):
            if not attributes.secure:
                return False, "__Secure- prefix requires Secure attribute"
        elif name_lower.startswith('__host-'):
            if not attributes.secure:
                return False, "__Host- prefix requires Secure attribute"
            if attributes.domain:
                return False, "__Host- prefix cannot have Domain attribute"
            if attributes.path != '/':
                return False, "__Host- prefix requires Path='/'"
        return True, None


class CookieCrypto:
    """
    Cryptographic operations for cookie encryption and signing.

    Provides AES encryption via Fernet and HMAC signing for cookie integrity.
    """

    def __init__(self, secret_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize cookie crypto handler.

        Args:
            secret_key: Secret key for encryption/signing (auto-generated if not provided)
            salt: Salt for key derivation (auto-generated if not provided)
        """
        if not CRYPTO_AVAILABLE:
            logger.warning("cryptography package not available, encryption features disabled")
            self.encryption_available = False
            return

        self.encryption_available = True
        self.secret_key = secret_key or self._generate_secret_key()
        self.salt = salt or secrets.token_bytes(16)

        # Derive encryption key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key_bytes = kdf.derive(self.secret_key.encode())
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    @staticmethod
    def _generate_secret_key() -> str:
        """Generate a secure random secret key."""
        return secrets.token_urlsafe(32)

    def encrypt(self, data: str) -> str:
        """
        Encrypt cookie data.

        Args:
            data: Plain text data to encrypt

        Returns:
            Encrypted data as base64 string
        """
        if not self.encryption_available:
            raise RuntimeError("Encryption not available - install cryptography package")

        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt cookie data.

        Args:
            encrypted_data: Encrypted data as base64 string

        Returns:
            Decrypted plain text data

        Raises:
            ValueError: If decryption fails
        """
        if not self.encryption_available:
            raise RuntimeError("Encryption not available - install cryptography package")

        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt cookie data: {e}")

    def sign(self, data: str) -> str:
        """
        Create HMAC signature for cookie data.

        Args:
            data: Data to sign

        Returns:
            HMAC signature as hex string
        """
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_signature(self, data: str, signature: str) -> bool:
        """
        Verify HMAC signature of cookie data.

        Args:
            data: Original data
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        expected_signature = self.sign(data)
        return hmac.compare_digest(signature, expected_signature)

    def create_signed_value(self, value: str) -> str:
        """
        Create signed cookie value.

        Args:
            value: Original value

        Returns:
            Signed value in format "value.signature"
        """
        signature = self.sign(value)
        return f"{value}.{signature}"

    def verify_signed_value(self, signed_value: str) -> Optional[str]:
        """
        Verify and extract original value from signed cookie.

        Args:
            signed_value: Signed value in format "value.signature"

        Returns:
            Original value if signature is valid, None otherwise
        """
        try:
            value, signature = signed_value.rsplit('.', 1)
            if self.verify_signature(value, signature):
                return value
            return None
        except ValueError:
            return None


class CookieJar:
    """
    Cookie jar for managing multiple cookies across domains.

    Provides efficient storage and retrieval of cookies with automatic
    expiration handling and domain/path matching.
    """

    def __init__(self):
        """Initialize empty cookie jar."""
        self.cookies: Dict[str, Dict[str, CookieAttributes]] = defaultdict(dict)
        self.domain_index: Dict[str, Set[str]] = defaultdict(set)
        self.stats = {
            'total_cookies': 0,
            'session_cookies': 0,
            'persistent_cookies': 0,
            'encrypted_cookies': 0,
            'signed_cookies': 0
        }

    def add(self, cookie: CookieAttributes) -> None:
        """
        Add cookie to jar.

        Args:
            cookie: Cookie attributes to add
        """
        domain = cookie.domain or '*'
        self.cookies[domain][cookie.name] = cookie
        self.domain_index[domain].add(cookie.name)
        self._update_stats()

    def get(self, name: str, domain: Optional[str] = None) -> Optional[CookieAttributes]:
        """
        Get cookie by name and optional domain.

        Args:
            name: Cookie name
            domain: Optional domain filter

        Returns:
            Cookie attributes if found and not expired
        """
        if domain:
            cookie = self.cookies.get(domain, {}).get(name)
            if cookie and not cookie.is_expired():
                cookie.last_accessed = datetime.now(timezone.utc)
                cookie.access_count += 1
                return cookie
        else:
            # Search all domains
            for domain_cookies in self.cookies.values():
                cookie = domain_cookies.get(name)
                if cookie and not cookie.is_expired():
                    cookie.last_accessed = datetime.now(timezone.utc)
                    cookie.access_count += 1
                    return cookie
        return None

    def get_all_for_domain(self, domain: str, path: str = '/') -> List[CookieAttributes]:
        """
        Get all cookies matching domain and path.

        Args:
            domain: Target domain
            path: Target path

        Returns:
            List of matching non-expired cookies
        """
        matching_cookies = []

        for cookie_domain, domain_cookies in self.cookies.items():
            for cookie in domain_cookies.values():
                if not cookie.is_expired() and cookie.matches_domain(domain) and cookie.matches_path(path):
                    cookie.last_accessed = datetime.now(timezone.utc)
                    cookie.access_count += 1
                    matching_cookies.append(cookie)

        return matching_cookies

    def remove(self, name: str, domain: Optional[str] = None) -> bool:
        """
        Remove cookie from jar.

        Args:
            name: Cookie name
            domain: Optional domain filter

        Returns:
            True if cookie was removed
        """
        if domain:
            if name in self.cookies.get(domain, {}):
                del self.cookies[domain][name]
                self.domain_index[domain].discard(name)
                self._update_stats()
                return True
        else:
            # Remove from all domains
            removed = False
            for domain, domain_cookies in list(self.cookies.items()):
                if name in domain_cookies:
                    del domain_cookies[name]
                    self.domain_index[domain].discard(name)
                    removed = True
            if removed:
                self._update_stats()
            return removed
        return False

    def clear_domain(self, domain: str) -> int:
        """
        Clear all cookies for a domain.

        Args:
            domain: Domain to clear

        Returns:
            Number of cookies removed
        """
        count = len(self.cookies.get(domain, {}))
        if domain in self.cookies:
            del self.cookies[domain]
            del self.domain_index[domain]
            self._update_stats()
        return count

    def clear_expired(self) -> int:
        """
        Remove all expired cookies.

        Returns:
            Number of cookies removed
        """
        count = 0
        for domain, domain_cookies in list(self.cookies.items()):
            for name, cookie in list(domain_cookies.items()):
                if cookie.is_expired():
                    del domain_cookies[name]
                    self.domain_index[domain].discard(name)
                    count += 1
        self._update_stats()
        return count

    def clear_all(self) -> int:
        """
        Clear all cookies from jar.

        Returns:
            Number of cookies removed
        """
        count = self.stats['total_cookies']
        self.cookies.clear()
        self.domain_index.clear()
        self._update_stats()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cookie jar statistics."""
        return self.stats.copy()

    def _update_stats(self) -> None:
        """Update internal statistics."""
        total = 0
        session = 0
        persistent = 0
        encrypted = 0
        signed = 0

        for domain_cookies in self.cookies.values():
            for cookie in domain_cookies.values():
                if not cookie.is_expired():
                    total += 1
                    if cookie.scope == CookieScope.SESSION:
                        session += 1
                    else:
                        persistent += 1
                    if cookie.encrypted:
                        encrypted += 1
                    if cookie.signed:
                        signed += 1

        self.stats = {
            'total_cookies': total,
            'session_cookies': session,
            'persistent_cookies': persistent,
            'encrypted_cookies': encrypted,
            'signed_cookies': signed
        }


class CookieHandlerFSA:
    """
    Comprehensive Finite State Automaton for HTTP Cookie Management.

    This FSA provides enterprise-grade cookie handling with:
    - Full CRUD operations (Create, Read, Update, Delete)
    - Security features (encryption, signing, HttpOnly, Secure, SameSite)
    - Session and persistent cookie management
    - Cookie expiration and max-age handling
    - Domain and path scope management
    - Cookie jar for multiple domains
    - GDPR compliance with consent tracking
    - Comprehensive validation
    - Integration with Session Manager FSA

    State transitions:
        UNINITIALIZED -> CREATED (create_cookie)
        CREATED -> VALIDATED (validate_cookie)
        VALIDATED -> ENCRYPTED (encrypt_cookie)
        VALIDATED -> SIGNED (sign_cookie)
        ENCRYPTED/SIGNED -> STORED (store_cookie)
        STORED -> RETRIEVED (get_cookie)
        RETRIEVED -> DELETED (delete_cookie)
        Any -> EXPIRED (auto-expiration)
        Any -> INVALID (validation failure)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        enable_encryption: bool = True,
        enable_signing: bool = True,
        enforce_secure: bool = True,
        storage_path: Optional[Union[str, Path]] = None,
        auto_clear_expired: bool = True
    ):
        """
        Initialize Cookie Handler FSA.

        Args:
            secret_key: Secret key for cryptographic operations
            enable_encryption: Enable cookie encryption
            enable_signing: Enable cookie signing
            enforce_secure: Enforce secure cookie attributes
            storage_path: Path for persistent cookie storage
            auto_clear_expired: Automatically clear expired cookies
        """
        self.state = CookieState.UNINITIALIZED
        self.enable_encryption = enable_encryption and CRYPTO_AVAILABLE
        self.enable_signing = enable_signing
        self.enforce_secure = enforce_secure
        self.auto_clear_expired = auto_clear_expired

        # Initialize crypto handler
        self.crypto = CookieCrypto(secret_key) if (enable_encryption or enable_signing) else None

        # Initialize cookie jar
        self.jar = CookieJar()

        # GDPR consent tracking
        self.consent_records: Dict[str, ConsentRecord] = {}

        # Storage path for persistence
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

        # Validation helper
        self.validator = CookieValidator()

        # Operation history for auditing
        self.operation_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

        logger.info(f"CookieHandlerFSA initialized with encryption={self.enable_encryption}, "
                   f"signing={self.enable_signing}, enforce_secure={self.enforce_secure}")

    def _transition_state(self, new_state: CookieState, operation: str, details: Optional[Dict] = None) -> None:
        """
        Transition FSA to new state and log operation.

        Args:
            new_state: Target state
            operation: Operation name
            details: Optional operation details
        """
        old_state = self.state
        self.state = new_state

        # Log state transition
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operation': operation,
            'from_state': old_state.value,
            'to_state': new_state.value,
            'details': details or {}
        }

        self.operation_history.append(log_entry)

        # Maintain history size limit
        if len(self.operation_history) > self.max_history_size:
            self.operation_history = self.operation_history[-self.max_history_size:]

        logger.debug(f"State transition: {old_state.value} -> {new_state.value} ({operation})")

    def create_cookie(
        self,
        name: str,
        value: str,
        domain: Optional[str] = None,
        path: str = "/",
        expires: Optional[Union[datetime, int]] = None,
        max_age: Optional[int] = None,
        secure: bool = True,
        http_only: bool = True,
        same_site: SameSitePolicy = SameSitePolicy.LAX,
        scope: CookieScope = CookieScope.SESSION,
        consent_type: ConsentType = ConsentType.STRICTLY_NECESSARY,
        encrypt: bool = False,
        sign: bool = False,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[CookieAttributes]:
        """
        Create a new cookie with specified attributes.

        Args:
            name: Cookie name
            value: Cookie value
            domain: Cookie domain (optional)
            path: Cookie path
            expires: Expiration datetime or seconds from now
            max_age: Maximum age in seconds
            secure: HTTPS only flag
            http_only: Prevent JavaScript access
            same_site: SameSite policy
            scope: Cookie scope type
            consent_type: GDPR consent category
            encrypt: Encrypt cookie value
            sign: Sign cookie value
            priority: Cookie priority
            metadata: Additional metadata

        Returns:
            Created cookie attributes or None if validation fails
        """
        try:
            # Validate cookie name
            valid, error = self.validator.validate_name(name)
            if not valid:
                logger.error(f"Invalid cookie name: {error}")
                self._transition_state(CookieState.INVALID, 'create_cookie', {'error': error})
                return None

            # Validate cookie value
            valid, error = self.validator.validate_value(value)
            if not valid:
                logger.error(f"Invalid cookie value: {error}")
                self._transition_state(CookieState.INVALID, 'create_cookie', {'error': error})
                return None

            # Validate domain
            if domain:
                valid, error = self.validator.validate_domain(domain)
                if not valid:
                    logger.error(f"Invalid domain: {error}")
                    self._transition_state(CookieState.INVALID, 'create_cookie', {'error': error})
                    return None

            # Validate path
            valid, error = self.validator.validate_path(path)
            if not valid:
                logger.error(f"Invalid path: {error}")
                self._transition_state(CookieState.INVALID, 'create_cookie', {'error': error})
                return None

            # Enforce secure flag if required
            if self.enforce_secure:
                secure = True

            # Process expires parameter
            expires_dt = None
            if expires:
                if isinstance(expires, int):
                    expires_dt = datetime.now(timezone.utc) + timedelta(seconds=expires)
                else:
                    expires_dt = expires

            # Create cookie attributes
            cookie = CookieAttributes(
                name=name,
                value=value,
                domain=domain,
                path=path,
                expires=expires_dt,
                max_age=max_age,
                secure=secure,
                http_only=http_only,
                same_site=same_site,
                scope=scope,
                consent_type=consent_type,
                encrypted=encrypt,
                signed=sign,
                priority=priority,
                metadata=metadata or {}
            )

            # Validate secure prefixes
            valid, error = self.validator.validate_secure_prefix(name, cookie)
            if not valid:
                logger.error(f"Invalid secure prefix: {error}")
                self._transition_state(CookieState.INVALID, 'create_cookie', {'error': error})
                return None

            self._transition_state(CookieState.CREATED, 'create_cookie', {'name': name, 'domain': domain})

            # Apply encryption if requested
            if encrypt and self.enable_encryption:
                cookie = self._encrypt_cookie(cookie)

            # Apply signing if requested
            if sign and self.enable_signing:
                cookie = self._sign_cookie(cookie)

            # Validate the complete cookie
            if self._validate_cookie(cookie):
                self._transition_state(CookieState.VALIDATED, 'validate_cookie', {'name': name})
                return cookie
            else:
                self._transition_state(CookieState.INVALID, 'validate_cookie', {'name': name})
                return None

        except Exception as e:
            logger.error(f"Failed to create cookie: {e}")
            self._transition_state(CookieState.INVALID, 'create_cookie', {'error': str(e)})
            return None

    def _encrypt_cookie(self, cookie: CookieAttributes) -> CookieAttributes:
        """
        Encrypt cookie value.

        Args:
            cookie: Cookie to encrypt

        Returns:
            Cookie with encrypted value
        """
        if not self.crypto or not self.enable_encryption:
            logger.warning("Encryption requested but not available")
            return cookie

        try:
            encrypted_value = self.crypto.encrypt(cookie.value)
            cookie.value = encrypted_value
            cookie.encrypted = True
            self._transition_state(CookieState.ENCRYPTED, 'encrypt_cookie', {'name': cookie.name})
            logger.debug(f"Cookie '{cookie.name}' encrypted")
        except Exception as e:
            logger.error(f"Failed to encrypt cookie: {e}")
            self._transition_state(CookieState.INVALID, 'encrypt_cookie', {'error': str(e)})

        return cookie

    def _decrypt_cookie(self, cookie: CookieAttributes) -> CookieAttributes:
        """
        Decrypt cookie value.

        Args:
            cookie: Cookie to decrypt

        Returns:
            Cookie with decrypted value
        """
        if not cookie.encrypted or not self.crypto:
            return cookie

        try:
            decrypted_value = self.crypto.decrypt(cookie.value)
            cookie.value = decrypted_value
            cookie.encrypted = False
            logger.debug(f"Cookie '{cookie.name}' decrypted")
        except Exception as e:
            logger.error(f"Failed to decrypt cookie: {e}")
            self._transition_state(CookieState.INVALID, 'decrypt_cookie', {'error': str(e)})

        return cookie

    def _sign_cookie(self, cookie: CookieAttributes) -> CookieAttributes:
        """
        Sign cookie value.

        Args:
            cookie: Cookie to sign

        Returns:
            Cookie with signed value
        """
        if not self.crypto or not self.enable_signing:
            logger.warning("Signing requested but not available")
            return cookie

        try:
            signed_value = self.crypto.create_signed_value(cookie.value)
            cookie.value = signed_value
            cookie.signed = True
            self._transition_state(CookieState.SIGNED, 'sign_cookie', {'name': cookie.name})
            logger.debug(f"Cookie '{cookie.name}' signed")
        except Exception as e:
            logger.error(f"Failed to sign cookie: {e}")
            self._transition_state(CookieState.INVALID, 'sign_cookie', {'error': str(e)})

        return cookie

    def _verify_signed_cookie(self, cookie: CookieAttributes) -> Optional[CookieAttributes]:
        """
        Verify and extract original value from signed cookie.

        Args:
            cookie: Cookie to verify

        Returns:
            Cookie with verified value or None if verification fails
        """
        if not cookie.signed or not self.crypto:
            return cookie

        try:
            original_value = self.crypto.verify_signed_value(cookie.value)
            if original_value is None:
                logger.error(f"Cookie '{cookie.name}' signature verification failed")
                return None
            cookie.value = original_value
            cookie.signed = False
            logger.debug(f"Cookie '{cookie.name}' signature verified")
            return cookie
        except Exception as e:
            logger.error(f"Failed to verify cookie signature: {e}")
            return None

    def _validate_cookie(self, cookie: CookieAttributes) -> bool:
        """
        Validate all cookie attributes.

        Args:
            cookie: Cookie to validate

        Returns:
            True if cookie is valid
        """
        # Check if expired
        if cookie.is_expired():
            logger.warning(f"Cookie '{cookie.name}' has expired")
            return False

        # Check security requirements
        if self.enforce_secure and not cookie.is_secure_enough():
            logger.warning(f"Cookie '{cookie.name}' does not meet security requirements")
            return False

        return True

    def store_cookie(self, cookie: CookieAttributes, user_id: Optional[str] = None) -> bool:
        """
        Store cookie in the cookie jar.

        Args:
            cookie: Cookie to store
            user_id: Optional user ID for GDPR consent check

        Returns:
            True if cookie was stored successfully
        """
        try:
            # Check GDPR consent if user_id provided
            if user_id and not self._check_consent(user_id, cookie.consent_type):
                logger.warning(f"User {user_id} has not consented to {cookie.consent_type.value} cookies")
                return False

            # Validate before storing
            if not self._validate_cookie(cookie):
                logger.error(f"Cookie validation failed for '{cookie.name}'")
                return False

            # Add to jar
            self.jar.add(cookie)
            self._transition_state(CookieState.STORED, 'store_cookie', {'name': cookie.name})

            # Persist if storage path configured
            if self.storage_path:
                self._persist_jar()

            logger.debug(f"Cookie '{cookie.name}' stored successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to store cookie: {e}")
            return False

    def get_cookie(
        self,
        name: str,
        domain: Optional[str] = None,
        decrypt: bool = False
    ) -> Optional[CookieAttributes]:
        """
        Retrieve cookie from jar.

        Args:
            name: Cookie name
            domain: Optional domain filter
            decrypt: Decrypt cookie value if encrypted

        Returns:
            Cookie attributes or None if not found
        """
        try:
            # Auto-clear expired cookies if enabled
            if self.auto_clear_expired:
                self.jar.clear_expired()

            cookie = self.jar.get(name, domain)
            if not cookie:
                logger.debug(f"Cookie '{name}' not found")
                return None

            self._transition_state(CookieState.RETRIEVED, 'get_cookie', {'name': name, 'domain': domain})

            # Verify signature if signed
            if cookie.signed:
                cookie = self._verify_signed_cookie(cookie)
                if not cookie:
                    return None

            # Decrypt if requested and encrypted
            if decrypt and cookie.encrypted:
                cookie = self._decrypt_cookie(cookie)

            return cookie

        except Exception as e:
            logger.error(f"Failed to get cookie: {e}")
            return None

    def get_cookies_for_request(
        self,
        url: str,
        decrypt: bool = False
    ) -> List[CookieAttributes]:
        """
        Get all cookies applicable for a request URL.

        Args:
            url: Request URL
            decrypt: Decrypt cookie values if encrypted

        Returns:
            List of applicable cookies
        """
        try:
            parsed = urlparse(url)
            domain = parsed.hostname or ''
            path = parsed.path or '/'

            cookies = self.jar.get_all_for_domain(domain, path)

            # Process each cookie
            processed_cookies = []
            for cookie in cookies:
                # Verify signature if signed
                if cookie.signed:
                    cookie = self._verify_signed_cookie(cookie)
                    if not cookie:
                        continue

                # Decrypt if requested
                if decrypt and cookie.encrypted:
                    cookie = self._decrypt_cookie(cookie)

                processed_cookies.append(cookie)

            return processed_cookies

        except Exception as e:
            logger.error(f"Failed to get cookies for request: {e}")
            return []

    def update_cookie(
        self,
        name: str,
        value: Optional[str] = None,
        domain: Optional[str] = None,
        **kwargs
    ) -> Optional[CookieAttributes]:
        """
        Update existing cookie.

        Args:
            name: Cookie name
            value: New value (optional)
            domain: Cookie domain
            **kwargs: Additional attributes to update

        Returns:
            Updated cookie or None if not found
        """
        try:
            # Get existing cookie
            existing = self.jar.get(name, domain)
            if not existing:
                logger.warning(f"Cookie '{name}' not found for update")
                return None

            # Update value if provided
            if value is not None:
                existing.value = value

            # Update other attributes
            for key, val in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)

            # Re-encrypt/sign if needed
            if existing.encrypted and self.enable_encryption:
                existing = self._encrypt_cookie(existing)
            if existing.signed and self.enable_signing:
                existing = self._sign_cookie(existing)

            # Re-validate and store
            if self._validate_cookie(existing):
                self.jar.add(existing)  # This will update existing cookie

                if self.storage_path:
                    self._persist_jar()

                logger.debug(f"Cookie '{name}' updated successfully")
                return existing
            else:
                logger.error(f"Updated cookie '{name}' failed validation")
                return None

        except Exception as e:
            logger.error(f"Failed to update cookie: {e}")
            return None

    def delete_cookie(self, name: str, domain: Optional[str] = None) -> bool:
        """
        Delete cookie from jar.

        Args:
            name: Cookie name
            domain: Optional domain filter

        Returns:
            True if cookie was deleted
        """
        try:
            removed = self.jar.remove(name, domain)
            if removed:
                self._transition_state(CookieState.DELETED, 'delete_cookie', {'name': name, 'domain': domain})

                if self.storage_path:
                    self._persist_jar()

                logger.debug(f"Cookie '{name}' deleted successfully")
            return removed

        except Exception as e:
            logger.error(f"Failed to delete cookie: {e}")
            return False

    def clear_cookies(self, domain: Optional[str] = None) -> int:
        """
        Clear cookies from jar.

        Args:
            domain: Optional domain filter (clears all if not specified)

        Returns:
            Number of cookies cleared
        """
        try:
            if domain:
                count = self.jar.clear_domain(domain)
            else:
                count = self.jar.clear_all()

            if self.storage_path:
                self._persist_jar()

            logger.info(f"Cleared {count} cookies" + (f" for domain {domain}" if domain else ""))
            return count

        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return 0

    def set_consent(
        self,
        user_id: str,
        consent_types: Set[ConsentType],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_in_days: int = 365
    ) -> ConsentRecord:
        """
        Record user's cookie consent.

        Args:
            user_id: User identifier
            consent_types: Set of consented cookie types
            ip_address: User's IP address
            user_agent: User's browser user agent
            expires_in_days: Consent validity period

        Returns:
            Created consent record
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        consent = ConsentRecord(
            user_id=user_id,
            consent_types=consent_types,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )

        self.consent_records[user_id] = consent
        logger.info(f"Consent recorded for user {user_id}: {[ct.value for ct in consent_types]}")

        return consent

    def get_consent(self, user_id: str) -> Optional[ConsentRecord]:
        """
        Get user's consent record.

        Args:
            user_id: User identifier

        Returns:
            Consent record or None
        """
        return self.consent_records.get(user_id)

    def _check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has given consent for cookie type.

        Args:
            user_id: User identifier
            consent_type: Cookie consent type

        Returns:
            True if consent is given and valid
        """
        # Strictly necessary cookies don't require consent
        if consent_type == ConsentType.STRICTLY_NECESSARY:
            return True

        consent = self.consent_records.get(user_id)
        if not consent:
            return False

        return consent.has_consent(consent_type)

    def export_cookies(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Export cookies as list of dictionaries.

        Args:
            domain: Optional domain filter

        Returns:
            List of cookie dictionaries
        """
        if domain:
            cookies = self.jar.get_all_for_domain(domain)
        else:
            cookies = []
            for domain_cookies in self.jar.cookies.values():
                cookies.extend(domain_cookies.values())

        return [cookie.to_dict() for cookie in cookies]

    def import_cookies(self, cookies_data: List[Dict[str, Any]]) -> int:
        """
        Import cookies from list of dictionaries.

        Args:
            cookies_data: List of cookie dictionaries

        Returns:
            Number of cookies imported
        """
        count = 0
        for cookie_dict in cookies_data:
            try:
                cookie = CookieAttributes.from_dict(cookie_dict)
                if self._validate_cookie(cookie):
                    self.jar.add(cookie)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to import cookie: {e}")

        logger.info(f"Imported {count} cookies")
        return count

    def _persist_jar(self) -> None:
        """Persist cookie jar to storage."""
        if not self.storage_path:
            return

        try:
            jar_file = self.storage_path / "cookie_jar.json"
            data = {
                'cookies': self.export_cookies(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            with open(jar_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist cookie jar: {e}")

    def load_jar(self) -> int:
        """
        Load cookie jar from storage.

        Returns:
            Number of cookies loaded
        """
        if not self.storage_path:
            return 0

        try:
            jar_file = self.storage_path / "cookie_jar.json"
            if not jar_file.exists():
                return 0

            with open(jar_file, 'r') as f:
                data = json.load(f)

            count = self.import_cookies(data.get('cookies', []))
            logger.info(f"Loaded {count} cookies from storage")
            return count

        except Exception as e:
            logger.error(f"Failed to load cookie jar: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Dictionary of statistics
        """
        jar_stats = self.jar.get_stats()

        return {
            'state': self.state.value,
            'jar_stats': jar_stats,
            'consent_records': len(self.consent_records),
            'encryption_enabled': self.enable_encryption,
            'signing_enabled': self.enable_signing,
            'enforce_secure': self.enforce_secure,
            'operations_count': len(self.operation_history)
        }

    def get_operation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get operation history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of operation log entries
        """
        if limit:
            return self.operation_history[-limit:]
        return self.operation_history.copy()

    def to_http_header(self, cookie: CookieAttributes) -> str:
        """
        Convert cookie to Set-Cookie HTTP header value.

        Args:
            cookie: Cookie to convert

        Returns:
            Set-Cookie header value
        """
        parts = [f"{cookie.name}={cookie.value}"]

        if cookie.domain:
            parts.append(f"Domain={cookie.domain}")

        if cookie.path:
            parts.append(f"Path={cookie.path}")

        if cookie.expires:
            expires_str = cookie.expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            parts.append(f"Expires={expires_str}")

        if cookie.max_age is not None:
            parts.append(f"Max-Age={cookie.max_age}")

        if cookie.secure:
            parts.append("Secure")

        if cookie.http_only:
            parts.append("HttpOnly")

        if cookie.same_site:
            parts.append(f"SameSite={cookie.same_site.value}")

        if cookie.priority and cookie.priority != "medium":
            parts.append(f"Priority={cookie.priority}")

        if cookie.partition_key:
            parts.append(f"Partitioned")

        return "; ".join(parts)

    def from_http_header(self, header: str) -> Optional[CookieAttributes]:
        """
        Parse Set-Cookie HTTP header into cookie attributes.

        Args:
            header: Set-Cookie header value

        Returns:
            Parsed cookie attributes or None if parsing fails
        """
        try:
            parts = [part.strip() for part in header.split(';')]
            if not parts:
                return None

            # Parse name=value
            name_value = parts[0].split('=', 1)
            if len(name_value) != 2:
                return None

            name, value = name_value

            # Default attributes
            attrs = {
                'name': name,
                'value': value,
                'domain': None,
                'path': '/',
                'expires': None,
                'max_age': None,
                'secure': False,
                'http_only': False,
                'same_site': SameSitePolicy.LAX
            }

            # Parse additional attributes
            for part in parts[1:]:
                if '=' in part:
                    key, val = part.split('=', 1)
                    key = key.strip().lower()
                    val = val.strip()

                    if key == 'domain':
                        attrs['domain'] = val
                    elif key == 'path':
                        attrs['path'] = val
                    elif key == 'expires':
                        # Parse expires date
                        try:
                            attrs['expires'] = datetime.strptime(val, "%a, %d %b %Y %H:%M:%S GMT")
                        except ValueError:
                            pass
                    elif key == 'max-age':
                        attrs['max_age'] = int(val)
                    elif key == 'samesite':
                        attrs['same_site'] = SameSitePolicy(val)
                else:
                    # Boolean flags
                    flag = part.strip().lower()
                    if flag == 'secure':
                        attrs['secure'] = True
                    elif flag == 'httponly':
                        attrs['http_only'] = True

            return CookieAttributes(**attrs)

        except Exception as e:
            logger.error(f"Failed to parse cookie header: {e}")
            return None

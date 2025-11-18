"""
Comprehensive test suite for Cookie Handler FSA.

Tests cover:
- Cookie CRUD operations
- Cookie validation
- Encryption and signing
- Session and persistent cookies
- Cookie expiration handling
- Domain and path matching
- Cookie jar management
- GDPR consent tracking
- Security features
- State transitions
- HTTP header parsing
"""

import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest

from agno.fsas.infrastructure.cookie_handler_fsa import (
    CookieAttributes,
    CookieHandlerFSA,
    CookieJar,
    CookieScope,
    CookieState,
    CookieValidator,
    ConsentRecord,
    ConsentType,
    SameSitePolicy,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for cookie storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def cookie_handler(temp_dir: Path) -> CookieHandlerFSA:
    """Create cookie handler with temporary storage."""
    return CookieHandlerFSA(
        secret_key="test-secret-key-12345",
        enable_encryption=True,
        enable_signing=True,
        enforce_secure=False,  # Allow non-secure for testing
        storage_path=temp_dir,
        auto_clear_expired=True
    )


@pytest.fixture
def cookie_jar() -> CookieJar:
    """Create empty cookie jar."""
    return CookieJar()


class TestCookieValidator:
    """Test suite for cookie validation."""

    def test_validate_valid_cookie_name(self):
        """Test validation of valid cookie names."""
        valid_names = ["session_id", "user-token", "auth_v2", "test123"]
        for name in valid_names:
            valid, error = CookieValidator.validate_name(name)
            assert valid is True
            assert error is None

    def test_validate_invalid_cookie_name(self):
        """Test validation of invalid cookie names."""
        # Empty name
        valid, error = CookieValidator.validate_name("")
        assert valid is False
        assert "cannot be empty" in error

        # Invalid characters
        valid, error = CookieValidator.validate_name("test cookie")
        assert valid is False
        assert "invalid characters" in error

        # Too long
        long_name = "a" * 300
        valid, error = CookieValidator.validate_name(long_name)
        assert valid is False
        assert "maximum length" in error

    def test_validate_valid_cookie_value(self):
        """Test validation of valid cookie values."""
        valid_values = ["simple", "value-with-dash", "value123", "a=b"]
        for value in valid_values:
            valid, error = CookieValidator.validate_value(value)
            assert valid is True
            assert error is None

    def test_validate_invalid_cookie_value(self):
        """Test validation of invalid cookie values."""
        # Too long
        long_value = "a" * 5000
        valid, error = CookieValidator.validate_value(long_value)
        assert valid is False
        assert "maximum length" in error

    def test_validate_valid_domain(self):
        """Test validation of valid domains."""
        valid_domains = ["example.com", ".example.com", "sub.example.com", ".sub.example.com"]
        for domain in valid_domains:
            valid, error = CookieValidator.validate_domain(domain)
            assert valid is True
            assert error is None

    def test_validate_invalid_domain(self):
        """Test validation of invalid domains."""
        # Invalid format
        valid, error = CookieValidator.validate_domain("example")
        assert valid is False
        assert "at least one dot" in error

        # Invalid characters
        valid, error = CookieValidator.validate_domain("exam ple.com")
        assert valid is False

    def test_validate_valid_path(self):
        """Test validation of valid paths."""
        valid_paths = ["/", "/app", "/app/user", "/path-with-dash"]
        for path in valid_paths:
            valid, error = CookieValidator.validate_path(path)
            assert valid is True
            assert error is None

    def test_validate_invalid_path(self):
        """Test validation of invalid paths."""
        # Empty path
        valid, error = CookieValidator.validate_path("")
        assert valid is False
        assert "cannot be empty" in error

        # Doesn't start with /
        valid, error = CookieValidator.validate_path("app")
        assert valid is False
        assert "must start with" in error

    def test_validate_secure_prefix(self):
        """Test validation of __Secure- and __Host- prefixes."""
        # __Secure- requires Secure attribute
        cookie = CookieAttributes(name="__Secure-token", value="test", secure=False)
        valid, error = CookieValidator.validate_secure_prefix("__Secure-token", cookie)
        assert valid is False
        assert "Secure attribute" in error

        cookie.secure = True
        valid, error = CookieValidator.validate_secure_prefix("__Secure-token", cookie)
        assert valid is True

        # __Host- requires Secure, no Domain, and Path=/
        cookie = CookieAttributes(name="__Host-token", value="test", secure=False, domain="example.com", path="/app")
        valid, error = CookieValidator.validate_secure_prefix("__Host-token", cookie)
        assert valid is False

        cookie.secure = True
        valid, error = CookieValidator.validate_secure_prefix("__Host-token", cookie)
        assert valid is False
        assert "cannot have Domain" in error

        cookie.domain = None
        valid, error = CookieValidator.validate_secure_prefix("__Host-token", cookie)
        assert valid is False
        assert "Path='/'" in error

        cookie.path = "/"
        valid, error = CookieValidator.validate_secure_prefix("__Host-token", cookie)
        assert valid is True


class TestCookieAttributes:
    """Test suite for cookie attributes."""

    def test_cookie_creation(self):
        """Test basic cookie creation."""
        cookie = CookieAttributes(
            name="session_id",
            value="abc123",
            domain=".example.com",
            path="/app",
            secure=True,
            http_only=True
        )

        assert cookie.name == "session_id"
        assert cookie.value == "abc123"
        assert cookie.domain == ".example.com"
        assert cookie.path == "/app"
        assert cookie.secure is True
        assert cookie.http_only is True

    def test_cookie_expiration(self):
        """Test cookie expiration check."""
        # Not expired
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        cookie = CookieAttributes(name="test", value="value", expires=future_time)
        assert cookie.is_expired() is False

        # Expired
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        cookie.expires = past_time
        assert cookie.is_expired() is True

        # Session cookie (no expiration)
        cookie.expires = None
        assert cookie.is_expired() is False

    def test_cookie_security_check(self):
        """Test cookie security requirements."""
        # Secure enough
        cookie = CookieAttributes(name="test", value="value", secure=True, http_only=True)
        assert cookie.is_secure_enough() is True

        # Not secure enough
        cookie.secure = False
        assert cookie.is_secure_enough() is False

        cookie.secure = True
        cookie.http_only = False
        assert cookie.is_secure_enough() is False

    def test_domain_matching(self):
        """Test domain matching logic."""
        # Exact match
        cookie = CookieAttributes(name="test", value="value", domain="example.com")
        assert cookie.matches_domain("example.com") is True
        assert cookie.matches_domain("other.com") is False

        # Subdomain match with leading dot
        cookie.domain = ".example.com"
        assert cookie.matches_domain("example.com") is True
        assert cookie.matches_domain("sub.example.com") is True
        assert cookie.matches_domain("other.com") is False

        # No domain (matches all)
        cookie.domain = None
        assert cookie.matches_domain("any.com") is True

    def test_path_matching(self):
        """Test path matching logic."""
        cookie = CookieAttributes(name="test", value="value", path="/app")
        assert cookie.matches_path("/app") is True
        assert cookie.matches_path("/app/user") is True
        assert cookie.matches_path("/other") is False
        assert cookie.matches_path("/ap") is False

    def test_cookie_serialization(self):
        """Test cookie to_dict and from_dict."""
        original = CookieAttributes(
            name="test",
            value="value",
            domain=".example.com",
            path="/app",
            secure=True,
            http_only=True,
            same_site=SameSitePolicy.STRICT,
            scope=CookieScope.PERSISTENT,
            consent_type=ConsentType.ANALYTICS
        )

        # Serialize
        data = original.to_dict()
        assert data['name'] == "test"
        assert data['value'] == "value"
        assert data['same_site'] == "Strict"
        assert data['scope'] == "persistent"
        assert data['consent_type'] == "analytics"

        # Deserialize
        restored = CookieAttributes.from_dict(data)
        assert restored.name == original.name
        assert restored.value == original.value
        assert restored.same_site == original.same_site
        assert restored.scope == original.scope
        assert restored.consent_type == original.consent_type


class TestCookieJar:
    """Test suite for cookie jar management."""

    def test_add_and_get_cookie(self, cookie_jar):
        """Test adding and retrieving cookies."""
        cookie = CookieAttributes(name="test", value="value", domain="example.com")
        cookie_jar.add(cookie)

        retrieved = cookie_jar.get("test", "example.com")
        assert retrieved is not None
        assert retrieved.name == "test"
        assert retrieved.value == "value"

    def test_get_nonexistent_cookie(self, cookie_jar):
        """Test getting non-existent cookie."""
        result = cookie_jar.get("nonexistent")
        assert result is None

    def test_get_expired_cookie(self, cookie_jar):
        """Test getting expired cookie."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        cookie = CookieAttributes(name="expired", value="value", expires=past_time)
        cookie_jar.add(cookie)

        result = cookie_jar.get("expired")
        assert result is None  # Expired cookies are not returned

    def test_get_all_for_domain(self, cookie_jar):
        """Test getting all cookies for a domain."""
        # Add cookies for different domains
        cookie1 = CookieAttributes(name="cookie1", value="val1", domain=".example.com", path="/")
        cookie2 = CookieAttributes(name="cookie2", value="val2", domain=".example.com", path="/app")
        cookie3 = CookieAttributes(name="cookie3", value="val3", domain="other.com", path="/")

        cookie_jar.add(cookie1)
        cookie_jar.add(cookie2)
        cookie_jar.add(cookie3)

        # Get cookies for example.com
        cookies = cookie_jar.get_all_for_domain("sub.example.com", "/")
        assert len(cookies) == 2  # cookie1 and cookie2 should match

        cookies = cookie_jar.get_all_for_domain("sub.example.com", "/app")
        assert len(cookies) == 2  # Both should match /app path

        cookies = cookie_jar.get_all_for_domain("other.com", "/")
        assert len(cookies) == 1

    def test_remove_cookie(self, cookie_jar):
        """Test removing cookies."""
        cookie = CookieAttributes(name="test", value="value", domain="example.com")
        cookie_jar.add(cookie)

        # Verify it exists
        assert cookie_jar.get("test", "example.com") is not None

        # Remove it
        removed = cookie_jar.remove("test", "example.com")
        assert removed is True

        # Verify it's gone
        assert cookie_jar.get("test", "example.com") is None

        # Try removing again
        removed = cookie_jar.remove("test", "example.com")
        assert removed is False

    def test_clear_domain(self, cookie_jar):
        """Test clearing all cookies for a domain."""
        cookie1 = CookieAttributes(name="cookie1", value="val1", domain="example.com")
        cookie2 = CookieAttributes(name="cookie2", value="val2", domain="example.com")
        cookie3 = CookieAttributes(name="cookie3", value="val3", domain="other.com")

        cookie_jar.add(cookie1)
        cookie_jar.add(cookie2)
        cookie_jar.add(cookie3)

        count = cookie_jar.clear_domain("example.com")
        assert count == 2

        # Verify example.com cookies are gone
        assert cookie_jar.get("cookie1", "example.com") is None
        assert cookie_jar.get("cookie2", "example.com") is None

        # Verify other.com cookie still exists
        assert cookie_jar.get("cookie3", "other.com") is not None

    def test_clear_expired(self, cookie_jar):
        """Test clearing expired cookies."""
        # Add mix of expired and valid cookies
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        cookie1 = CookieAttributes(name="valid", value="val1", expires=future_time)
        cookie2 = CookieAttributes(name="expired1", value="val2", expires=past_time)
        cookie3 = CookieAttributes(name="expired2", value="val3", expires=past_time)

        cookie_jar.add(cookie1)
        cookie_jar.add(cookie2)
        cookie_jar.add(cookie3)

        count = cookie_jar.clear_expired()
        assert count == 2

        # Verify only valid cookie remains
        assert cookie_jar.get("valid") is not None
        assert cookie_jar.get("expired1") is None
        assert cookie_jar.get("expired2") is None

    def test_clear_all(self, cookie_jar):
        """Test clearing all cookies."""
        cookie1 = CookieAttributes(name="cookie1", value="val1")
        cookie2 = CookieAttributes(name="cookie2", value="val2")

        cookie_jar.add(cookie1)
        cookie_jar.add(cookie2)

        count = cookie_jar.clear_all()
        assert count == 2

        assert cookie_jar.get("cookie1") is None
        assert cookie_jar.get("cookie2") is None

    def test_jar_statistics(self, cookie_jar):
        """Test cookie jar statistics."""
        # Add different types of cookies
        session_cookie = CookieAttributes(
            name="session",
            value="val",
            scope=CookieScope.SESSION
        )
        persistent_cookie = CookieAttributes(
            name="persistent",
            value="val",
            scope=CookieScope.PERSISTENT,
            encrypted=True
        )
        signed_cookie = CookieAttributes(
            name="signed",
            value="val",
            signed=True
        )

        cookie_jar.add(session_cookie)
        cookie_jar.add(persistent_cookie)
        cookie_jar.add(signed_cookie)

        stats = cookie_jar.get_stats()
        assert stats['total_cookies'] == 3
        assert stats['session_cookies'] == 1
        assert stats['persistent_cookies'] == 2
        assert stats['encrypted_cookies'] == 1
        assert stats['signed_cookies'] == 1


class TestConsentRecord:
    """Test suite for GDPR consent tracking."""

    def test_consent_creation(self):
        """Test consent record creation."""
        consent = ConsentRecord(
            user_id="user123",
            consent_types={ConsentType.STRICTLY_NECESSARY, ConsentType.ANALYTICS},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert consent.user_id == "user123"
        assert ConsentType.STRICTLY_NECESSARY in consent.consent_types
        assert ConsentType.ANALYTICS in consent.consent_types
        assert consent.ip_address == "192.168.1.1"

    def test_has_consent(self):
        """Test consent checking."""
        consent = ConsentRecord(
            user_id="user123",
            consent_types={ConsentType.STRICTLY_NECESSARY, ConsentType.FUNCTIONAL}
        )

        assert consent.has_consent(ConsentType.STRICTLY_NECESSARY) is True
        assert consent.has_consent(ConsentType.FUNCTIONAL) is True
        assert consent.has_consent(ConsentType.ANALYTICS) is False
        assert consent.has_consent(ConsentType.ADVERTISING) is False

    def test_consent_expiration(self):
        """Test consent expiration."""
        future_time = datetime.now(timezone.utc) + timedelta(days=30)
        consent = ConsentRecord(
            user_id="user123",
            consent_types={ConsentType.ANALYTICS},
            expires_at=future_time
        )

        assert consent.is_expired() is False
        assert consent.has_consent(ConsentType.ANALYTICS) is True

        # Set to past
        past_time = datetime.now(timezone.utc) - timedelta(days=1)
        consent.expires_at = past_time

        assert consent.is_expired() is True
        assert consent.has_consent(ConsentType.ANALYTICS) is False  # Expired consent = no consent

    def test_consent_serialization(self):
        """Test consent record serialization."""
        original = ConsentRecord(
            user_id="user123",
            consent_types={ConsentType.ANALYTICS, ConsentType.FUNCTIONAL},
            ip_address="192.168.1.1"
        )

        # Serialize
        data = original.to_dict()
        assert data['user_id'] == "user123"
        assert 'analytics' in data['consent_types']
        assert 'functional' in data['consent_types']

        # Deserialize
        restored = ConsentRecord.from_dict(data)
        assert restored.user_id == original.user_id
        assert restored.consent_types == original.consent_types


class TestCookieHandlerFSA:
    """Test suite for Cookie Handler FSA."""

    def test_initialization(self, cookie_handler):
        """Test FSA initialization."""
        assert cookie_handler.state == CookieState.UNINITIALIZED
        assert cookie_handler.jar is not None
        assert cookie_handler.crypto is not None

    def test_create_simple_cookie(self, cookie_handler):
        """Test creating a simple cookie."""
        cookie = cookie_handler.create_cookie(
            name="session_id",
            value="abc123",
            domain=".example.com"
        )

        assert cookie is not None
        assert cookie.name == "session_id"
        assert cookie.value == "abc123"
        assert cookie.domain == ".example.com"
        assert cookie_handler.state == CookieState.VALIDATED

    def test_create_cookie_with_expiration(self, cookie_handler):
        """Test creating cookie with expiration."""
        # Using seconds
        cookie = cookie_handler.create_cookie(
            name="temp",
            value="value",
            expires=3600  # 1 hour
        )

        assert cookie is not None
        assert cookie.expires is not None
        assert cookie.expires > datetime.now(timezone.utc)

        # Using datetime
        future_time = datetime.now(timezone.utc) + timedelta(days=7)
        cookie = cookie_handler.create_cookie(
            name="persistent",
            value="value",
            expires=future_time
        )

        assert cookie is not None
        assert cookie.expires == future_time

    def test_create_invalid_cookie(self, cookie_handler):
        """Test creating cookie with invalid attributes."""
        # Invalid name
        cookie = cookie_handler.create_cookie(
            name="invalid name",  # Space is invalid
            value="value"
        )
        assert cookie is None
        assert cookie_handler.state == CookieState.INVALID

    def test_store_and_retrieve_cookie(self, cookie_handler):
        """Test storing and retrieving cookies."""
        cookie = cookie_handler.create_cookie(
            name="test",
            value="value123",
            domain="example.com"
        )

        # Store
        stored = cookie_handler.store_cookie(cookie)
        assert stored is True

        # Retrieve
        retrieved = cookie_handler.get_cookie("test", "example.com")
        assert retrieved is not None
        assert retrieved.name == "test"
        assert retrieved.value == "value123"

    def test_update_cookie(self, cookie_handler):
        """Test updating existing cookie."""
        # Create and store
        cookie = cookie_handler.create_cookie(name="test", value="original")
        cookie_handler.store_cookie(cookie)

        # Update
        updated = cookie_handler.update_cookie(
            name="test",
            value="updated",
            domain=None
        )

        assert updated is not None
        assert updated.value == "updated"

        # Verify in jar
        retrieved = cookie_handler.get_cookie("test")
        assert retrieved.value == "updated"

    def test_delete_cookie(self, cookie_handler):
        """Test deleting cookies."""
        # Create and store
        cookie = cookie_handler.create_cookie(name="test", value="value")
        cookie_handler.store_cookie(cookie)

        # Verify exists
        assert cookie_handler.get_cookie("test") is not None

        # Delete
        deleted = cookie_handler.delete_cookie("test")
        assert deleted is True

        # Verify gone
        assert cookie_handler.get_cookie("test") is None

    def test_clear_cookies(self, cookie_handler):
        """Test clearing cookies."""
        # Create and store multiple cookies
        cookie1 = cookie_handler.create_cookie(name="cookie1", value="val1", domain="example.com")
        cookie2 = cookie_handler.create_cookie(name="cookie2", value="val2", domain="example.com")
        cookie3 = cookie_handler.create_cookie(name="cookie3", value="val3", domain="other.com")

        cookie_handler.store_cookie(cookie1)
        cookie_handler.store_cookie(cookie2)
        cookie_handler.store_cookie(cookie3)

        # Clear specific domain
        count = cookie_handler.clear_cookies(domain="example.com")
        assert count == 2

        # Clear all
        count = cookie_handler.clear_cookies()
        assert count == 1  # Only other.com cookie left

    def test_encrypted_cookie(self, cookie_handler):
        """Test cookie encryption."""
        cookie = cookie_handler.create_cookie(
            name="secret",
            value="sensitive_data",
            encrypt=True
        )

        assert cookie is not None
        assert cookie.encrypted is True
        assert cookie.value != "sensitive_data"  # Should be encrypted

        # Store and retrieve with decryption
        cookie_handler.store_cookie(cookie)
        retrieved = cookie_handler.get_cookie("secret", decrypt=True)

        assert retrieved is not None
        assert retrieved.value == "sensitive_data"  # Should be decrypted

    def test_signed_cookie(self, cookie_handler):
        """Test cookie signing."""
        cookie = cookie_handler.create_cookie(
            name="verified",
            value="important_data",
            sign=True
        )

        assert cookie is not None
        assert cookie.signed is True
        assert "." in cookie.value  # Signature format: value.signature

        # Store and retrieve (signature verification happens automatically)
        cookie_handler.store_cookie(cookie)
        retrieved = cookie_handler.get_cookie("verified")

        assert retrieved is not None
        assert retrieved.value == "important_data"  # Signature verified and removed

    def test_consent_tracking(self, cookie_handler):
        """Test GDPR consent tracking."""
        # Set consent
        consent = cookie_handler.set_consent(
            user_id="user123",
            consent_types={ConsentType.STRICTLY_NECESSARY, ConsentType.ANALYTICS},
            ip_address="192.168.1.1"
        )

        assert consent is not None
        assert consent.user_id == "user123"

        # Get consent
        retrieved = cookie_handler.get_consent("user123")
        assert retrieved is not None
        assert ConsentType.ANALYTICS in retrieved.consent_types

        # Store cookie requiring consent
        cookie = cookie_handler.create_cookie(
            name="analytics",
            value="data",
            consent_type=ConsentType.ANALYTICS
        )

        # Should succeed with consent
        stored = cookie_handler.store_cookie(cookie, user_id="user123")
        assert stored is True

        # Should fail without consent for advertising
        ad_cookie = cookie_handler.create_cookie(
            name="ad",
            value="data",
            consent_type=ConsentType.ADVERTISING
        )
        stored = cookie_handler.store_cookie(ad_cookie, user_id="user123")
        assert stored is False

    def test_get_cookies_for_request(self, cookie_handler):
        """Test getting cookies for a specific request URL."""
        # Create cookies with different scopes
        cookie1 = cookie_handler.create_cookie(
            name="cookie1",
            value="val1",
            domain=".example.com",
            path="/"
        )
        cookie2 = cookie_handler.create_cookie(
            name="cookie2",
            value="val2",
            domain=".example.com",
            path="/app"
        )
        cookie3 = cookie_handler.create_cookie(
            name="cookie3",
            value="val3",
            domain="other.com",
            path="/"
        )

        cookie_handler.store_cookie(cookie1)
        cookie_handler.store_cookie(cookie2)
        cookie_handler.store_cookie(cookie3)

        # Get cookies for specific URL
        cookies = cookie_handler.get_cookies_for_request("https://www.example.com/")
        assert len(cookies) == 1  # Only cookie1 matches

        cookies = cookie_handler.get_cookies_for_request("https://www.example.com/app/page")
        assert len(cookies) == 2  # cookie1 and cookie2 match

        cookies = cookie_handler.get_cookies_for_request("https://other.com/")
        assert len(cookies) == 1  # Only cookie3 matches

    def test_export_import_cookies(self, cookie_handler):
        """Test exporting and importing cookies."""
        # Create and store cookies
        cookie1 = cookie_handler.create_cookie(name="cookie1", value="val1")
        cookie2 = cookie_handler.create_cookie(name="cookie2", value="val2")

        cookie_handler.store_cookie(cookie1)
        cookie_handler.store_cookie(cookie2)

        # Export
        exported = cookie_handler.export_cookies()
        assert len(exported) == 2

        # Clear and import
        cookie_handler.clear_cookies()
        count = cookie_handler.import_cookies(exported)
        assert count == 2

        # Verify imported
        assert cookie_handler.get_cookie("cookie1") is not None
        assert cookie_handler.get_cookie("cookie2") is not None

    def test_persistence(self, cookie_handler, temp_dir):
        """Test cookie persistence to disk."""
        # Create and store cookies
        cookie1 = cookie_handler.create_cookie(name="persistent1", value="val1")
        cookie2 = cookie_handler.create_cookie(name="persistent2", value="val2")

        cookie_handler.store_cookie(cookie1)
        cookie_handler.store_cookie(cookie2)

        # Verify file was created
        jar_file = temp_dir / "cookie_jar.json"
        assert jar_file.exists()

        # Create new handler and load
        new_handler = CookieHandlerFSA(storage_path=temp_dir, enforce_secure=False)
        count = new_handler.load_jar()
        assert count == 2

        # Verify cookies loaded
        assert new_handler.get_cookie("persistent1") is not None
        assert new_handler.get_cookie("persistent2") is not None

    def test_http_header_conversion(self, cookie_handler):
        """Test conversion to/from HTTP Set-Cookie header."""
        # Create cookie
        cookie = cookie_handler.create_cookie(
            name="session",
            value="abc123",
            domain=".example.com",
            path="/app",
            max_age=3600,
            secure=True,
            http_only=True,
            same_site=SameSitePolicy.STRICT
        )

        # Convert to header
        header = cookie_handler.to_http_header(cookie)
        assert "session=abc123" in header
        assert "Domain=.example.com" in header
        assert "Path=/app" in header
        assert "Max-Age=3600" in header
        assert "Secure" in header
        assert "HttpOnly" in header
        assert "SameSite=Strict" in header

    def test_http_header_parsing(self, cookie_handler):
        """Test parsing HTTP Set-Cookie header."""
        header = "session=abc123; Domain=.example.com; Path=/; Max-Age=3600; Secure; HttpOnly; SameSite=Lax"

        cookie = cookie_handler.from_http_header(header)
        assert cookie is not None
        assert cookie.name == "session"
        assert cookie.value == "abc123"
        assert cookie.domain == ".example.com"
        assert cookie.path == "/"
        assert cookie.max_age == 3600
        assert cookie.secure is True
        assert cookie.http_only is True
        assert cookie.same_site == SameSitePolicy.LAX

    def test_statistics(self, cookie_handler):
        """Test getting FSA statistics."""
        # Create and store different types of cookies
        session = cookie_handler.create_cookie(
            name="session",
            value="val",
            scope=CookieScope.SESSION
        )
        persistent = cookie_handler.create_cookie(
            name="persistent",
            value="val",
            scope=CookieScope.PERSISTENT,
            encrypt=True
        )

        cookie_handler.store_cookie(session)
        cookie_handler.store_cookie(persistent)

        stats = cookie_handler.get_stats()
        assert stats['jar_stats']['total_cookies'] == 2
        assert stats['jar_stats']['session_cookies'] == 1
        assert stats['jar_stats']['persistent_cookies'] == 1
        assert stats['encryption_enabled'] is True
        assert stats['signing_enabled'] is True

    def test_operation_history(self, cookie_handler):
        """Test operation history tracking."""
        # Perform operations
        cookie = cookie_handler.create_cookie(name="test", value="value")
        cookie_handler.store_cookie(cookie)
        cookie_handler.get_cookie("test")
        cookie_handler.delete_cookie("test")

        # Get history
        history = cookie_handler.get_operation_history()
        assert len(history) > 0

        # Check recent operations
        recent = cookie_handler.get_operation_history(limit=2)
        assert len(recent) == 2

    def test_state_transitions(self, cookie_handler):
        """Test FSA state transitions."""
        assert cookie_handler.state == CookieState.UNINITIALIZED

        # Create cookie -> VALIDATED
        cookie = cookie_handler.create_cookie(name="test", value="value")
        assert cookie_handler.state == CookieState.VALIDATED

        # Store cookie -> STORED
        cookie_handler.store_cookie(cookie)
        assert cookie_handler.state == CookieState.STORED

        # Get cookie -> RETRIEVED
        cookie_handler.get_cookie("test")
        assert cookie_handler.state == CookieState.RETRIEVED

        # Delete cookie -> DELETED
        cookie_handler.delete_cookie("test")
        assert cookie_handler.state == CookieState.DELETED

        # Invalid operation -> INVALID
        bad_cookie = cookie_handler.create_cookie(name="bad name", value="value")
        assert bad_cookie is None
        assert cookie_handler.state == CookieState.INVALID

    def test_auto_clear_expired_cookies(self, cookie_handler):
        """Test automatic clearing of expired cookies."""
        # Create expired cookie
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_cookie = cookie_handler.create_cookie(
            name="expired",
            value="value",
            expires=past_time
        )

        # Even though validation passes at creation, it expires immediately
        # Store valid cookie first
        valid_cookie = cookie_handler.create_cookie(
            name="valid",
            value="value",
            expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        cookie_handler.store_cookie(valid_cookie)

        # Manually add expired cookie to jar for testing
        expired_attr = CookieAttributes(
            name="expired",
            value="value",
            expires=past_time
        )
        cookie_handler.jar.add(expired_attr)

        # Get cookie should trigger auto-clear
        result = cookie_handler.get_cookie("expired")
        assert result is None  # Expired cookie should not be returned

        # Valid cookie should still be there
        result = cookie_handler.get_cookie("valid")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

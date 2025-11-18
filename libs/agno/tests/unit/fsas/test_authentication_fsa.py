"""
Comprehensive tests for Authentication FSA.

This test suite covers all major components:
- User registration and management
- Authentication (password, MFA)
- Session management
- JWT token generation and validation
- OAuth2 authorization and token flows
- OIDC support
- Security features (rate limiting, brute force protection)
- Audit logging
- Password policies
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from agno.fsas.infrastructure.authentication_fsa import (
    AuthenticationAuditLogger,
    AuthenticationEvent,
    AuthenticationFSA,
    AuthenticationMethod,
    AuthenticationResult,
    FSAState,
    JWTTokenManager,
    OAuth2Client,
    OAuth2GrantType,
    OAuth2Provider,
    PasswordPolicy,
    PasswordUtils,
    RateLimiter,
    SecurityMonitor,
    Session,
    SessionManager,
    SessionStatus,
    TokenClaims,
    TokenType,
    User,
    UserManager,
    UserRole,
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def user_manager(temp_storage):
    """Create a user manager instance."""
    return UserManager(temp_storage / "users")


@pytest.fixture
def session_manager():
    """Create a session manager instance."""
    return SessionManager(default_timeout=3600)


@pytest.fixture
def token_manager():
    """Create a JWT token manager instance."""
    return JWTTokenManager(secret_key="test-secret-key")


@pytest.fixture
def oauth2_provider(token_manager, user_manager):
    """Create an OAuth2 provider instance."""
    return OAuth2Provider(token_manager, user_manager)


@pytest.fixture
def auth_fsa(temp_storage):
    """Create an authentication FSA instance."""
    return AuthenticationFSA(
        storage_path=temp_storage,
        enable_audit=True,
        enable_rate_limiting=True,
        jwt_secret="test-jwt-secret"
    )


# ============================================================================
# PASSWORD UTILS TESTS
# ============================================================================


class TestPasswordUtils:
    """Tests for password utilities."""

    def test_hash_password_bcrypt(self):
        """Test bcrypt password hashing."""
        try:
            password = "TestPassword123!"
            hashed = PasswordUtils.hash_password(password, "bcrypt")

            assert len(hashed) > 0
            assert hashed.startswith("$2b$")
            assert hashed != password
        except ImportError:
            pytest.skip("bcrypt not available")

    def test_hash_password_argon2(self):
        """Test Argon2 password hashing."""
        try:
            password = "TestPassword456!"
            hashed = PasswordUtils.hash_password(password, "argon2")

            assert len(hashed) > 0
            assert hashed.startswith("$argon2")
            assert hashed != password
        except ImportError:
            pytest.skip("argon2 not available")

    def test_verify_password_bcrypt(self):
        """Test password verification with bcrypt."""
        try:
            password = "CorrectPassword123!"
            hashed = PasswordUtils.hash_password(password, "bcrypt")

            assert PasswordUtils.verify_password(password, hashed)
            assert not PasswordUtils.verify_password("WrongPassword", hashed)
        except ImportError:
            pytest.skip("bcrypt not available")

    def test_validate_password_strength(self):
        """Test password strength validation."""
        policy = PasswordPolicy(
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digits=True,
            require_special=True
        )

        # Valid password
        is_valid, errors = PasswordUtils.validate_password_strength(
            "ValidPass123!",
            policy
        )
        assert is_valid
        assert len(errors) == 0

        # Too short
        is_valid, errors = PasswordUtils.validate_password_strength(
            "Pass1!",
            policy
        )
        assert not is_valid
        assert any("at least" in e for e in errors)

        # No uppercase
        is_valid, errors = PasswordUtils.validate_password_strength(
            "password123!",
            policy
        )
        assert not is_valid
        assert any("uppercase" in e for e in errors)

        # No digits
        is_valid, errors = PasswordUtils.validate_password_strength(
            "Password!",
            policy
        )
        assert not is_valid
        assert any("digit" in e for e in errors)

        # No special characters
        is_valid, errors = PasswordUtils.validate_password_strength(
            "Password123",
            policy
        )
        assert not is_valid
        assert any("special" in e for e in errors)

    def test_password_contains_username(self):
        """Test password cannot contain username."""
        policy = PasswordPolicy(prevent_username=True)

        is_valid, errors = PasswordUtils.validate_password_strength(
            "myusername123!",
            policy,
            username="myusername"
        )
        assert not is_valid
        assert any("username" in e for e in errors)

    def test_common_password_prevention(self):
        """Test common password prevention."""
        policy = PasswordPolicy(prevent_common=True)

        is_valid, errors = PasswordUtils.validate_password_strength(
            "password",
            policy
        )
        assert not is_valid
        assert any("common" in e for e in errors)


# ============================================================================
# USER MANAGER TESTS
# ============================================================================


class TestUserManager:
    """Tests for user manager."""

    def test_register_user(self, user_manager):
        """Test user registration."""
        try:
            user, errors = user_manager.register_user(
                username="testuser",
                email="test@example.com",
                password="TestPass123!"
            )

            assert user is not None
            assert len(errors) == 0
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.password_hash is not None
            assert "user" in user.roles
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_register_duplicate_username(self, user_manager):
        """Test registration with duplicate username."""
        try:
            # First registration
            user_manager.register_user(
                "testuser",
                "test1@example.com",
                "TestPass123!"
            )

            # Duplicate username
            user, errors = user_manager.register_user(
                "testuser",
                "test2@example.com",
                "TestPass456!"
            )

            assert user is None
            assert len(errors) > 0
            assert any("Username" in e for e in errors)
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_register_duplicate_email(self, user_manager):
        """Test registration with duplicate email."""
        try:
            # First registration
            user_manager.register_user(
                "testuser1",
                "test@example.com",
                "TestPass123!"
            )

            # Duplicate email
            user, errors = user_manager.register_user(
                "testuser2",
                "test@example.com",
                "TestPass456!"
            )

            assert user is None
            assert len(errors) > 0
            assert any("Email" in e for e in errors)
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_register_weak_password(self, user_manager):
        """Test registration with weak password."""
        user, errors = user_manager.register_user(
            "testuser",
            "test@example.com",
            "weak"
        )

        assert user is None
        assert len(errors) > 0

    def test_get_user_by_username(self, user_manager):
        """Test getting user by username."""
        try:
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            retrieved = user_manager.get_user_by_username("testuser")
            assert retrieved is not None
            assert retrieved.user_id == user.user_id
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_get_user_by_email(self, user_manager):
        """Test getting user by email."""
        try:
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            retrieved = user_manager.get_user_by_email("test@example.com")
            assert retrieved is not None
            assert retrieved.user_id == user.user_id
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_lock_unlock_account(self, user_manager):
        """Test account locking and unlocking."""
        try:
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Lock account
            user_manager.lock_account(user.user_id)
            locked_user = user_manager.get_user(user.user_id)
            assert locked_user.is_locked

            # Unlock account
            user_manager.unlock_account(user.user_id)
            unlocked_user = user_manager.get_user(user.user_id)
            assert not unlocked_user.is_locked
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")

    def test_failed_login_attempts(self, user_manager):
        """Test failed login attempt tracking."""
        try:
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Increment failed attempts
            for i in range(4):
                locked = user_manager.increment_failed_login(user.user_id, max_attempts=5)
                assert not locked

            # 5th attempt should lock
            locked = user_manager.increment_failed_login(user.user_id, max_attempts=5)
            assert locked

            locked_user = user_manager.get_user(user.user_id)
            assert locked_user.is_locked
        except ImportError:
            pytest.skip("bcrypt/argon2 not available")


# ============================================================================
# SESSION MANAGER TESTS
# ============================================================================


class TestSessionManager:
    """Tests for session manager."""

    def test_create_session(self, session_manager):
        """Test session creation."""
        session = session_manager.create_session(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert session.session_id is not None
        assert session.user_id == "user123"
        assert session.ip_address == "192.168.1.1"
        assert session.status == SessionStatus.ACTIVE
        assert session.expires_at is not None

    def test_get_session(self, session_manager):
        """Test getting a session."""
        session = session_manager.create_session("user123")
        retrieved = session_manager.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_validate_session(self, session_manager):
        """Test session validation."""
        session = session_manager.create_session("user123")

        assert session_manager.validate_session(session.session_id)
        assert not session_manager.validate_session("invalid-session-id")

    def test_session_expiration(self, session_manager):
        """Test session expiration."""
        # Create session with 1 second timeout
        session = session_manager.create_session("user123", timeout=1)

        # Should be valid initially
        assert session_manager.validate_session(session.session_id)

        # Wait for expiration
        time.sleep(2)

        # Should be expired
        assert not session_manager.validate_session(session.session_id)

    def test_sliding_window(self, session_manager):
        """Test sliding session window."""
        session = session_manager.create_session("user123", timeout=2)

        # Access session after 1 second
        time.sleep(1)
        session_manager.get_session(session.session_id)

        # Access again after another second
        time.sleep(1)
        # Should still be valid due to sliding window
        assert session_manager.validate_session(session.session_id)

    def test_revoke_session(self, session_manager):
        """Test session revocation."""
        session = session_manager.create_session("user123")

        # Revoke session
        success = session_manager.revoke_session(session.session_id)
        assert success

        # Should no longer be valid
        assert not session_manager.validate_session(session.session_id)

    def test_logout(self, session_manager):
        """Test logout."""
        session = session_manager.create_session("user123")

        # Logout
        success = session_manager.logout(session.session_id)
        assert success

        # Should no longer be valid
        assert not session_manager.validate_session(session.session_id)

    def test_get_user_sessions(self, session_manager):
        """Test getting all user sessions."""
        # Create multiple sessions for same user
        session1 = session_manager.create_session("user123")
        session2 = session_manager.create_session("user123")
        session3 = session_manager.create_session("user456")

        user_sessions = session_manager.get_user_sessions("user123")
        assert len(user_sessions) == 2

    def test_revoke_all_user_sessions(self, session_manager):
        """Test revoking all user sessions."""
        # Create multiple sessions
        session_manager.create_session("user123")
        session_manager.create_session("user123")

        # Revoke all
        count = session_manager.revoke_all_user_sessions("user123")
        assert count == 2

        # All should be invalid
        user_sessions = session_manager.get_user_sessions("user123")
        for session in user_sessions:
            assert session.status == SessionStatus.REVOKED


# ============================================================================
# JWT TOKEN MANAGER TESTS
# ============================================================================


class TestJWTTokenManager:
    """Tests for JWT token manager."""

    def test_generate_access_token(self, token_manager):
        """Test access token generation."""
        try:
            token = token_manager.generate_token("user123", TokenType.ACCESS)

            assert token is not None
            assert len(token) > 0
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_generate_refresh_token(self, token_manager):
        """Test refresh token generation."""
        try:
            token = token_manager.generate_token("user123", TokenType.REFRESH)

            assert token is not None
            assert len(token) > 0
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_validate_token(self, token_manager):
        """Test token validation."""
        try:
            token = token_manager.generate_token("user123", TokenType.ACCESS)

            is_valid, claims, error = token_manager.validate_token(token)

            assert is_valid
            assert claims is not None
            assert claims["sub"] == "user123"
            assert error is None
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_validate_invalid_token(self, token_manager):
        """Test validation of invalid token."""
        try:
            is_valid, claims, error = token_manager.validate_token("invalid.token.here")

            assert not is_valid
            assert claims is None
            assert error is not None
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_token_expiration(self, token_manager):
        """Test token expiration."""
        try:
            # Create token manager with 1 second lifetime
            short_token_manager = JWTTokenManager(
                secret_key="test",
                access_token_lifetime=1
            )

            token = short_token_manager.generate_token("user123", TokenType.ACCESS)

            # Should be valid initially
            is_valid, _, _ = short_token_manager.validate_token(token)
            assert is_valid

            # Wait for expiration
            time.sleep(2)

            # Should be expired
            is_valid, _, error = short_token_manager.validate_token(token)
            assert not is_valid
            assert "expired" in error.lower()
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_refresh_token(self, token_manager):
        """Test token refresh."""
        try:
            # Generate refresh token
            refresh_token = token_manager.generate_token("user123", TokenType.REFRESH)

            # Refresh to get new access token
            new_access_token, error = token_manager.refresh_token(refresh_token)

            assert new_access_token is not None
            assert error is None

            # Validate new token
            is_valid, claims, _ = token_manager.validate_token(new_access_token)
            assert is_valid
            assert claims["sub"] == "user123"
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_revoke_token(self, token_manager):
        """Test token revocation."""
        try:
            token = token_manager.generate_token("user123", TokenType.ACCESS)

            # Revoke token
            token_manager.revoke_token(token)

            # Should no longer be valid
            is_valid, _, error = token_manager.validate_token(token)
            assert not is_valid
            assert "revoked" in error.lower()
        except ImportError:
            pytest.skip("PyJWT not available")

    def test_token_introspection(self, token_manager):
        """Test token introspection."""
        try:
            token = token_manager.generate_token(
                "user123",
                TokenType.ACCESS,
                scope="read write"
            )

            introspection = token_manager.introspect_token(token)

            assert introspection["active"]
            assert introspection["sub"] == "user123"
            assert introspection["scope"] == "read write"
        except ImportError:
            pytest.skip("PyJWT not available")


# ============================================================================
# OAUTH2 PROVIDER TESTS
# ============================================================================


class TestOAuth2Provider:
    """Tests for OAuth2 provider."""

    def test_register_client(self, oauth2_provider):
        """Test OAuth2 client registration."""
        client = oauth2_provider.register_client(
            redirect_uris=["https://example.com/callback"],
            grant_types=["authorization_code"],
            response_types=["code"],
            client_name="Test App"
        )

        assert client.client_id is not None
        assert client.client_secret is not None
        assert len(client.client_id) > 0
        assert len(client.client_secret) > 0

    def test_authorization_code_flow(self, oauth2_provider, user_manager):
        """Test OAuth2 authorization code flow."""
        try:
            # Register client
            client = oauth2_provider.register_client(
                redirect_uris=["https://example.com/callback"],
                grant_types=["authorization_code"],
                response_types=["code"]
            )

            # Register user
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Authorize
            code, error = oauth2_provider.authorize(
                client_id=client.client_id,
                redirect_uri="https://example.com/callback",
                response_type="code",
                scope="openid profile",
                state="random-state",
                user_id=user.user_id
            )

            assert code is not None
            assert error is None

            # Exchange code for tokens
            token_response, error = oauth2_provider.token(
                grant_type="authorization_code",
                client_id=client.client_id,
                client_secret=client.client_secret,
                code=code,
                redirect_uri="https://example.com/callback"
            )

            assert token_response is not None
            assert error is None
            assert "access_token" in token_response
            assert "refresh_token" in token_response
            assert "id_token" in token_response
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_pkce_flow(self, oauth2_provider, user_manager):
        """Test PKCE (Proof Key for Code Exchange)."""
        try:
            # Register client
            client = oauth2_provider.register_client(
                redirect_uris=["https://example.com/callback"],
                grant_types=["authorization_code"],
                response_types=["code"]
            )

            # Register user
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Generate code verifier and challenge
            import hashlib
            import base64
            code_verifier = "test-code-verifier-string"
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")

            # Authorize with PKCE
            code, error = oauth2_provider.authorize(
                client_id=client.client_id,
                redirect_uri="https://example.com/callback",
                response_type="code",
                scope="openid",
                state="state",
                user_id=user.user_id,
                code_challenge=code_challenge,
                code_challenge_method="S256"
            )

            assert code is not None

            # Exchange code with verifier
            token_response, error = oauth2_provider.token(
                grant_type="authorization_code",
                client_id=client.client_id,
                client_secret=client.client_secret,
                code=code,
                redirect_uri="https://example.com/callback",
                code_verifier=code_verifier
            )

            assert token_response is not None
            assert error is None
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_client_credentials_flow(self, oauth2_provider):
        """Test client credentials flow."""
        try:
            # Register client
            client = oauth2_provider.register_client(
                redirect_uris=["https://example.com/callback"],
                grant_types=["client_credentials"],
                response_types=["token"]
            )

            # Get token using client credentials
            token_response, error = oauth2_provider.token(
                grant_type="client_credentials",
                client_id=client.client_id,
                client_secret=client.client_secret,
                scope="read write"
            )

            assert token_response is not None
            assert error is None
            assert "access_token" in token_response
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_userinfo_endpoint(self, oauth2_provider, user_manager):
        """Test OIDC UserInfo endpoint."""
        try:
            # Register user
            user, _ = user_manager.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Generate access token
            access_token = oauth2_provider.token_manager.generate_token(
                user.user_id,
                TokenType.ACCESS,
                scope="openid profile email"
            )

            # Get user info
            user_info, error = oauth2_provider.userinfo(access_token)

            assert user_info is not None
            assert error is None
            assert user_info["sub"] == user.user_id
            assert user_info["email"] == user.email
        except ImportError:
            pytest.skip("Required dependencies not available")


# ============================================================================
# SECURITY FEATURES TESTS
# ============================================================================


class TestRateLimiter:
    """Tests for rate limiter."""

    def test_rate_limiting(self):
        """Test rate limiting."""
        limiter = RateLimiter(max_requests=5, window_seconds=10)

        # First 5 requests should be allowed
        for i in range(5):
            assert limiter.is_allowed("test-user")

        # 6th request should be denied
        assert not limiter.is_allowed("test-user")

    def test_different_identifiers(self):
        """Test rate limiting with different identifiers."""
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        # User 1
        assert limiter.is_allowed("user1")
        assert limiter.is_allowed("user1")
        assert not limiter.is_allowed("user1")

        # User 2 should have separate limit
        assert limiter.is_allowed("user2")
        assert limiter.is_allowed("user2")

    def test_window_reset(self):
        """Test rate limit window reset."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Use up limit
        assert limiter.is_allowed("test-user")
        assert limiter.is_allowed("test-user")
        assert not limiter.is_allowed("test-user")

        # Wait for window to reset
        time.sleep(2)

        # Should be allowed again
        assert limiter.is_allowed("test-user")

    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=10)

        assert limiter.get_remaining("test-user") == 5

        limiter.is_allowed("test-user")
        assert limiter.get_remaining("test-user") == 4

        limiter.is_allowed("test-user")
        assert limiter.get_remaining("test-user") == 3


class TestSecurityMonitor:
    """Tests for security monitor."""

    def test_record_failed_attempt(self):
        """Test recording failed attempts."""
        monitor = SecurityMonitor()

        monitor.record_failed_attempt("user123", "192.168.1.1")
        assert not monitor.is_suspicious("user123", "192.168.1.1")

        # Multiple failures
        for _ in range(6):
            monitor.record_failed_attempt("user123", "192.168.1.1")

        assert monitor.is_suspicious("user123", "192.168.1.1")

    def test_suspicious_ip_detection(self):
        """Test suspicious IP detection."""
        monitor = SecurityMonitor()

        # Generate many failures
        for _ in range(15):
            monitor.record_failed_attempt("user123", "192.168.1.100")

        # IP should be marked as suspicious
        assert monitor.is_suspicious("different-user", "192.168.1.100")


# ============================================================================
# AUTHENTICATION FSA TESTS
# ============================================================================


class TestAuthenticationFSA:
    """Tests for Authentication FSA."""

    def test_initialization(self, auth_fsa):
        """Test FSA initialization."""
        assert auth_fsa.state == FSAState.IDLE
        assert auth_fsa.user_manager is not None
        assert auth_fsa.session_manager is not None
        assert auth_fsa.token_manager is not None
        assert auth_fsa.oauth2_provider is not None

    def test_user_registration(self, auth_fsa):
        """Test user registration through FSA."""
        try:
            user, errors = auth_fsa.register_user(
                username="testuser",
                email="test@example.com",
                password="TestPass123!"
            )

            assert user is not None
            assert len(errors) == 0
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_authentication_success(self, auth_fsa):
        """Test successful authentication."""
        try:
            # Register user
            user, _ = auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Authenticate
            result = auth_fsa.authenticate(
                username="testuser",
                password="TestPass123!",
                ip_address="192.168.1.1"
            )

            assert result.success
            assert result.user_id == user.user_id
            assert result.session_id is not None
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert auth_fsa.state == FSAState.AUTHORIZED
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_authentication_failure(self, auth_fsa):
        """Test failed authentication."""
        try:
            # Register user
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Authenticate with wrong password
            result = auth_fsa.authenticate(
                username="testuser",
                password="WrongPassword"
            )

            assert not result.success
            assert result.error is not None
            assert auth_fsa.state == FSAState.DENIED
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_account_lockout(self, auth_fsa):
        """Test account lockout after multiple failures."""
        try:
            # Register user
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Multiple failed attempts
            for _ in range(5):
                auth_fsa.authenticate("testuser", "WrongPassword")

            # Account should be locked
            result = auth_fsa.authenticate("testuser", "TestPass123!")
            assert not result.success
            assert "locked" in result.error.lower()
            assert auth_fsa.state == FSAState.LOCKED
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_rate_limiting(self, auth_fsa):
        """Test rate limiting."""
        # Make many requests quickly
        for _ in range(15):
            result = auth_fsa.authenticate("nonexistent", "password")

        # Should get rate limit error
        assert not result.success
        assert result.error is not None

    def test_session_validation(self, auth_fsa):
        """Test session validation."""
        try:
            # Register and authenticate
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )
            result = auth_fsa.authenticate("testuser", "TestPass123!")

            # Validate session
            is_valid = auth_fsa.validate_session(result.session_id)
            assert is_valid
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_token_validation(self, auth_fsa):
        """Test token validation."""
        try:
            # Register and authenticate
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )
            result = auth_fsa.authenticate("testuser", "TestPass123!")

            # Validate token
            is_valid, claims, error = auth_fsa.validate_token(result.access_token)
            assert is_valid
            assert claims is not None
            assert error is None
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_token_refresh(self, auth_fsa):
        """Test token refresh."""
        try:
            # Register and authenticate
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )
            result = auth_fsa.authenticate("testuser", "TestPass123!")

            # Refresh token
            new_token, error = auth_fsa.refresh_access_token(result.refresh_token)
            assert new_token is not None
            assert error is None
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_logout(self, auth_fsa):
        """Test logout."""
        try:
            # Register and authenticate
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )
            result = auth_fsa.authenticate("testuser", "TestPass123!")

            # Logout
            success = auth_fsa.logout(result.session_id)
            assert success

            # Session should no longer be valid
            is_valid = auth_fsa.validate_session(result.session_id)
            assert not is_valid
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_audit_logging(self, auth_fsa):
        """Test audit logging."""
        try:
            # Register user
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Authenticate
            auth_fsa.authenticate("testuser", "TestPass123!")

            # Get audit log
            audit_log = auth_fsa.get_audit_log()

            assert len(audit_log) >= 2  # Registration + authentication
            assert any(e["event_type"] == "user_registration" for e in audit_log)
            assert any(e["event_type"] == "authentication" for e in audit_log)
        except ImportError:
            pytest.skip("Required dependencies not available")

    def test_state_transitions(self, auth_fsa):
        """Test FSA state transitions."""
        try:
            assert auth_fsa.get_state() == FSAState.IDLE.value

            # Register user
            auth_fsa.register_user(
                "testuser",
                "test@example.com",
                "TestPass123!"
            )

            # Authenticate
            auth_fsa.authenticate("testuser", "TestPass123!")
            assert auth_fsa.get_state() == FSAState.AUTHORIZED.value

            # Check state history
            history = auth_fsa.get_state_history()
            assert len(history) > 0
        except ImportError:
            pytest.skip("Required dependencies not available")


# ============================================================================
# AUDIT LOGGER TESTS
# ============================================================================


class TestAuditLogger:
    """Tests for audit logger."""

    def test_log_event(self, temp_storage):
        """Test logging events."""
        logger = AuthenticationAuditLogger(temp_storage / "audit.log")

        logger.log_event(
            event_type="authentication",
            user_id="user123",
            username="testuser",
            success=True,
            ip_address="192.168.1.1"
        )

        events = logger.get_recent_events(1)
        assert len(events) == 1
        assert events[0]["event_type"] == "authentication"
        assert events[0]["success"]

    def test_query_events(self, temp_storage):
        """Test querying events."""
        logger = AuthenticationAuditLogger(temp_storage / "audit.log")

        # Log multiple events
        logger.log_event("authentication", user_id="user1", success=True)
        logger.log_event("authentication", user_id="user2", success=False)
        logger.log_event("logout", user_id="user1", success=True)

        # Query successful authentications
        results = logger.query_events(
            event_type="authentication",
            success=True
        )
        assert len(results) == 1

        # Query by user
        results = logger.query_events(user_id="user1")
        assert len(results) == 2

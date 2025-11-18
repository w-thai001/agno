"""
Comprehensive tests for Authentication FSA.

Tests cover:
- Password hashing and validation
- TOTP/HOTP generation and verification
- JWT token management
- OAuth2 flows
- Session management
- Multi-factor authentication
- Security features
- User account management
- Main authentication FSA
"""

import time
from datetime import datetime, timedelta

import pytest

from agno.fsas.infrastructure.authentication_fsa import (
    AuthenticationFSA,
    AuthenticationMethod,
    AuthenticationState,
    Credentials,
    HashAlgorithm,
    HOTPGenerator,
    JWTManager,
    MFAManager,
    MFAMethod,
    OAuth2Config,
    OAuth2Flow,
    OAuth2Provider,
    PasswordHasher,
    PasswordPolicy,
    PasswordValidator,
    SecurityConfig,
    SecurityManager,
    Session,
    SessionManager,
    SessionPersistence,
    TOTPGenerator,
    TokenType,
    User,
    UserAccountManager,
)


# ============================================================================
# Password Hashing Tests
# ============================================================================


class TestPasswordHasher:
    """Tests for PasswordHasher class."""

    def test_bcrypt_hash_and_verify(self):
        """Test bcrypt password hashing and verification."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        password = "SecurePassword123!"
        password_hash = hasher.hash_password(password)

        assert password_hash is not None
        assert len(password_hash) > 0
        assert hasher.verify_password(password, password_hash)
        assert not hasher.verify_password("WrongPassword", password_hash)

    def test_scrypt_hash_and_verify(self):
        """Test scrypt password hashing and verification."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.SCRYPT)
        password = "AnotherSecurePass456@"
        password_hash = hasher.hash_password(password)

        assert password_hash.startswith("$scrypt$")
        assert hasher.verify_password(password, password_hash)
        assert not hasher.verify_password("WrongPassword", password_hash)

    def test_pbkdf2_hash_and_verify(self):
        """Test PBKDF2 password hashing and verification."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.PBKDF2)
        password = "PBKDF2Test789#"
        password_hash = hasher.hash_password(password)

        assert password_hash.startswith("$pbkdf2$")
        assert hasher.verify_password(password, password_hash)
        assert not hasher.verify_password("WrongPassword", password_hash)

    def test_different_hashes_for_same_password(self):
        """Test that same password generates different hashes (salt)."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        password = "TestPassword123"
        hash1 = hasher.hash_password(password)
        hash2 = hasher.hash_password(password)

        assert hash1 != hash2
        assert hasher.verify_password(password, hash1)
        assert hasher.verify_password(password, hash2)


class TestPasswordValidator:
    """Tests for PasswordValidator class."""

    def test_password_length_validation(self):
        """Test password length requirements."""
        policy = PasswordPolicy(min_length=8, max_length=20)
        validator = PasswordValidator(policy)

        # Too short
        is_valid, errors = validator.validate("Short1!")
        assert not is_valid
        assert any("at least 8" in error for error in errors)

        # Too long
        is_valid, errors = validator.validate("VeryLongPassword123456789!")
        assert not is_valid
        assert any("at most 20" in error for error in errors)

        # Valid length
        is_valid, errors = validator.validate("ValidPass123!")
        assert is_valid

    def test_password_character_requirements(self):
        """Test password character requirements."""
        policy = PasswordPolicy(
            require_uppercase=True, require_lowercase=True, require_digits=True, require_special_chars=True
        )
        validator = PasswordValidator(policy)

        # Missing uppercase
        is_valid, errors = validator.validate("lowercase123!")
        assert not is_valid
        assert any("uppercase" in error for error in errors)

        # Missing lowercase
        is_valid, errors = validator.validate("UPPERCASE123!")
        assert not is_valid
        assert any("lowercase" in error for error in errors)

        # Missing digits
        is_valid, errors = validator.validate("Password!")
        assert not is_valid
        assert any("digit" in error for error in errors)

        # Missing special chars
        is_valid, errors = validator.validate("Password123")
        assert not is_valid
        assert any("special" in error for error in errors)

        # Valid password
        is_valid, errors = validator.validate("ValidPass123!")
        assert is_valid
        assert len(errors) == 0

    def test_common_password_prevention(self):
        """Test common password prevention."""
        policy = PasswordPolicy(prevent_common=True)
        validator = PasswordValidator(policy)

        is_valid, errors = validator.validate("password")
        assert not is_valid
        assert any("common" in error for error in errors)

    def test_username_in_password_prevention(self):
        """Test username in password prevention."""
        policy = PasswordPolicy(prevent_username=True)
        validator = PasswordValidator(policy)

        is_valid, errors = validator.validate("MyUser123!", username="myuser")
        assert not is_valid
        assert any("username" in error for error in errors)

        is_valid, errors = validator.validate("DifferentPass123!", username="myuser")
        assert is_valid

    def test_password_history_check(self):
        """Test password history checking."""
        policy = PasswordPolicy(history_count=3)
        validator = PasswordValidator(policy)
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)

        old_passwords = ["OldPass1!", "OldPass2!", "OldPass3!"]
        password_history = [hasher.hash_password(pwd) for pwd in old_passwords]

        # Try to reuse old password
        assert validator.check_password_history("OldPass2!", password_history, hasher)

        # New password should be allowed
        assert not validator.check_password_history("NewPass123!", password_history, hasher)


# ============================================================================
# TOTP/HOTP Tests
# ============================================================================


class TestTOTPGenerator:
    """Tests for TOTP generator."""

    def test_generate_secret(self):
        """Test TOTP secret generation."""
        totp = TOTPGenerator()
        secret = totp.generate_secret()

        assert secret is not None
        assert len(secret) > 0
        assert secret.isupper()

    def test_generate_totp_code(self):
        """Test TOTP code generation."""
        totp = TOTPGenerator()
        secret = totp.generate_secret()
        code = totp.generate_totp(secret)

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_code(self):
        """Test TOTP code verification."""
        totp = TOTPGenerator()
        secret = totp.generate_secret()
        code = totp.generate_totp(secret)

        # Should verify current code
        assert totp.verify_totp(secret, code)

        # Should not verify wrong code
        assert not totp.verify_totp(secret, "000000")

    def test_totp_time_window(self):
        """Test TOTP time window verification."""
        totp = TOTPGenerator()
        secret = totp.generate_secret()

        # Generate code for current time
        current_time = int(time.time())
        code = totp.generate_totp(secret, current_time)

        # Should verify with window
        assert totp.verify_totp(secret, code, window=1)

        # Generate code for past time (outside window)
        past_time = current_time - 120  # 2 intervals back
        old_code = totp.generate_totp(secret, past_time)
        assert not totp.verify_totp(secret, old_code, window=1)

    def test_provisioning_uri(self):
        """Test TOTP provisioning URI generation."""
        totp = TOTPGenerator()
        secret = totp.generate_secret()
        uri = totp.get_provisioning_uri(secret, "user@example.com", "AgnoAuth")

        assert uri.startswith("otpauth://totp/")
        assert "user@example.com" in uri
        assert "AgnoAuth" in uri
        assert f"secret={secret}" in uri


class TestHOTPGenerator:
    """Tests for HOTP generator."""

    def test_generate_hotp_code(self):
        """Test HOTP code generation."""
        hotp = HOTPGenerator()
        secret = hotp.generate_secret()
        code = hotp.generate_hotp(secret, counter=0)

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_hotp_counter_increment(self):
        """Test HOTP counter-based generation."""
        hotp = HOTPGenerator()
        secret = hotp.generate_secret()

        code1 = hotp.generate_hotp(secret, counter=0)
        code2 = hotp.generate_hotp(secret, counter=1)
        code3 = hotp.generate_hotp(secret, counter=2)

        # Different counters should generate different codes
        assert code1 != code2
        assert code2 != code3

        # Same counter should generate same code
        assert code1 == hotp.generate_hotp(secret, counter=0)

    def test_verify_hotp_code(self):
        """Test HOTP code verification with look-ahead."""
        hotp = HOTPGenerator()
        secret = hotp.generate_secret()

        # Generate code for counter 5
        code = hotp.generate_hotp(secret, counter=5)

        # Should verify with look-ahead from counter 0
        is_valid, new_counter = hotp.verify_hotp(secret, code, counter=0, look_ahead=10)
        assert is_valid
        assert new_counter == 6  # Counter should increment

        # Should not verify outside look-ahead window
        code_far = hotp.generate_hotp(secret, counter=50)
        is_valid, new_counter = hotp.verify_hotp(secret, code_far, counter=0, look_ahead=10)
        assert not is_valid


# ============================================================================
# JWT Token Management Tests
# ============================================================================


class TestJWTManager:
    """Tests for JWT token manager."""

    def test_generate_access_token(self):
        """Test access token generation."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        token = jwt_manager.generate_token(subject="user123", token_type=TokenType.ACCESS_TOKEN)

        assert token is not None
        assert len(token.split(".")) == 3  # Header.Payload.Signature

    def test_validate_token(self):
        """Test token validation."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        token = jwt_manager.generate_token(subject="user123")

        is_valid, payload, error = jwt_manager.validate_token(token)
        assert is_valid
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["iss"] == "test_issuer"
        assert error is None

    def test_expired_token(self):
        """Test expired token validation."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        token = jwt_manager.generate_token(subject="user123", expires_in=-10)  # Already expired

        is_valid, payload, error = jwt_manager.validate_token(token)
        assert not is_valid
        assert "expired" in error.lower()

    def test_invalid_signature(self):
        """Test token with invalid signature."""
        jwt_manager1 = JWTManager(secret_key="secret1", issuer="test_issuer", audience="test_audience")
        jwt_manager2 = JWTManager(secret_key="secret2", issuer="test_issuer", audience="test_audience")

        token = jwt_manager1.generate_token(subject="user123")

        # Try to validate with different secret
        is_valid, payload, error = jwt_manager2.validate_token(token)
        assert not is_valid

    def test_token_scopes(self):
        """Test token with scopes."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        scopes = ["read", "write", "admin"]
        token = jwt_manager.generate_token(subject="user123", scopes=scopes)

        is_valid, payload, error = jwt_manager.validate_token(token)
        assert is_valid
        assert payload["scope"] == "read write admin"

    def test_refresh_token(self):
        """Test refresh token flow."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        refresh_token = jwt_manager.generate_token(subject="user123", token_type=TokenType.REFRESH_TOKEN, expires_in=3600)

        # Generate new access token from refresh token
        access_token = jwt_manager.refresh_token(refresh_token)
        assert access_token is not None

        # Validate new access token
        is_valid, payload, error = jwt_manager.validate_token(access_token, TokenType.ACCESS_TOKEN)
        assert is_valid
        assert payload["sub"] == "user123"


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManager:
    """Tests for session manager."""

    def test_create_session(self):
        """Test session creation."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        assert session is not None
        assert session.user_id == "user123"
        assert session.access_token is not None
        assert session.is_valid

    def test_get_session(self):
        """Test session retrieval."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        retrieved = session_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.user_id == "user123"

    def test_validate_session(self):
        """Test session validation."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        is_valid, validated_session, error = session_manager.validate_session(session.session_id)
        assert is_valid
        assert validated_session is not None
        assert error is None

    def test_session_expiration(self):
        """Test session expiration."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        # Force expiration
        session.expires_at = datetime.utcnow() - timedelta(seconds=10)
        session_manager._store_session(session)

        is_valid, validated_session, error = session_manager.validate_session(session.session_id)
        assert not is_valid
        assert "expired" in error.lower()

    def test_session_idle_timeout(self):
        """Test session idle timeout."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")
        session.idle_timeout = 1  # 1 second

        # Force idle timeout
        session.last_activity = datetime.utcnow() - timedelta(seconds=10)
        session_manager._store_session(session)

        is_valid, validated_session, error = session_manager.validate_session(session.session_id)
        assert not is_valid
        assert "idle" in error.lower()

    def test_refresh_session(self):
        """Test session activity refresh."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        old_activity = session.last_activity
        time.sleep(0.1)

        success = session_manager.refresh_session(session.session_id)
        assert success

        refreshed = session_manager.get_session(session.session_id)
        assert refreshed.last_activity > old_activity

    def test_invalidate_session(self):
        """Test session invalidation."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123")

        success = session_manager.invalidate_session(session.session_id)
        assert success

        is_valid, validated_session, error = session_manager.validate_session(session.session_id)
        assert not is_valid
        assert "invalidated" in error.lower()

    def test_remember_me_session(self):
        """Test remember me session with extended duration."""
        session_manager = SessionManager()
        session = session_manager.create_session(user_id="user123", remember_me=True)

        assert session.remember_me
        assert session.absolute_timeout == 30 * 24 * 3600  # 30 days


# ============================================================================
# MFA Tests
# ============================================================================


class TestMFAManager:
    """Tests for MFA manager."""

    def test_enroll_totp(self):
        """Test TOTP enrollment."""
        mfa_manager = MFAManager()
        secret, provisioning_uri = mfa_manager.enroll_totp(user_id="user123")

        assert secret is not None
        assert len(secret) > 0
        assert provisioning_uri.startswith("otpauth://totp/")

    def test_verify_totp_enrollment(self):
        """Test TOTP enrollment verification."""
        mfa_manager = MFAManager()
        secret, _ = mfa_manager.enroll_totp(user_id="user123")

        # Generate valid code
        totp = TOTPGenerator()
        code = totp.generate_totp(secret)

        # Verify enrollment
        is_verified = mfa_manager.verify_totp_enrollment(user_id="user123", code=code)
        assert is_verified

        # Wrong code should fail
        is_verified = mfa_manager.verify_totp_enrollment(user_id="user123", code="000000")
        assert not is_verified

    def test_generate_mfa_challenge(self):
        """Test MFA challenge generation."""
        mfa_manager = MFAManager()
        challenge = mfa_manager.generate_mfa_challenge(user_id="user123", method=MFAMethod.SMS)

        assert challenge is not None
        assert challenge.user_id == "user123"
        assert challenge.method == MFAMethod.SMS
        assert challenge.code is not None
        assert len(challenge.code) == 6

    def test_verify_mfa_challenge(self):
        """Test MFA challenge verification."""
        mfa_manager = MFAManager()
        challenge = mfa_manager.generate_mfa_challenge(user_id="user123", method=MFAMethod.SMS)

        # Verify with correct code
        is_valid, error = mfa_manager.verify_mfa_challenge(challenge.challenge_id, challenge.code)
        assert is_valid
        assert error is None

    def test_mfa_challenge_expiration(self):
        """Test MFA challenge expiration."""
        mfa_manager = MFAManager()
        challenge = mfa_manager.generate_mfa_challenge(user_id="user123", method=MFAMethod.SMS)

        # Force expiration
        challenge.expires_at = datetime.utcnow() - timedelta(seconds=10)

        is_valid, error = mfa_manager.verify_mfa_challenge(challenge.challenge_id, challenge.code)
        assert not is_valid
        assert "expired" in error.lower()

    def test_mfa_max_attempts(self):
        """Test MFA maximum attempts."""
        mfa_manager = MFAManager()
        challenge = mfa_manager.generate_mfa_challenge(user_id="user123", method=MFAMethod.SMS)
        challenge.max_attempts = 3

        # Exhaust attempts
        for _ in range(3):
            mfa_manager.verify_mfa_challenge(challenge.challenge_id, "000000")

        # Next attempt should fail
        is_valid, error = mfa_manager.verify_mfa_challenge(challenge.challenge_id, challenge.code)
        assert not is_valid
        assert "max attempts" in error.lower()

    def test_generate_backup_codes(self):
        """Test backup code generation."""
        mfa_manager = MFAManager()
        codes = mfa_manager.generate_backup_codes(user_id="user123")

        assert len(codes) == 10
        for code in codes:
            assert len(code) == 8
            assert code.isupper()

        # Codes should be unique
        assert len(set(codes)) == len(codes)

    def test_verify_backup_code(self):
        """Test backup code verification."""
        mfa_manager = MFAManager()
        codes = mfa_manager.generate_backup_codes(user_id="user123")

        # Use first code
        is_valid, error = mfa_manager._verify_backup_code(user_id="user123", code=codes[0])
        assert is_valid

        # Same code should not work again
        is_valid, error = mfa_manager._verify_backup_code(user_id="user123", code=codes[0])
        assert not is_valid


# ============================================================================
# Security Features Tests
# ============================================================================


class TestSecurityManager:
    """Tests for security manager."""

    def test_rate_limiting(self):
        """Test rate limiting."""
        config = SecurityConfig(rate_limit_window=60, rate_limit_max_requests=3)
        security_manager = SecurityManager(config)

        # Should allow first 3 requests
        for _ in range(3):
            is_allowed, error = security_manager.check_rate_limit("192.168.1.1")
            assert is_allowed

        # 4th request should be blocked
        is_allowed, error = security_manager.check_rate_limit("192.168.1.1")
        assert not is_allowed
        assert "rate limit" in error.lower()

    def test_ip_blocking(self):
        """Test IP blocking."""
        config = SecurityConfig(enable_ip_blocking=True)
        config.blocked_ips.add("10.0.0.1")
        security_manager = SecurityManager(config)

        assert security_manager.check_ip_blocked("10.0.0.1")
        assert not security_manager.check_ip_blocked("192.168.1.1")

    def test_ip_allowlist(self):
        """Test IP allowlist."""
        config = SecurityConfig(enable_ip_blocking=True)
        config.allowed_ips.add("192.168.1.1")
        security_manager = SecurityManager(config)

        assert not security_manager.check_ip_blocked("192.168.1.1")
        assert security_manager.check_ip_blocked("10.0.0.1")

    def test_failed_login_attempts(self):
        """Test failed login attempt tracking."""
        config = SecurityConfig(max_failed_attempts=3, lockout_duration=60)
        security_manager = SecurityManager(config)

        # Record attempts
        for i in range(2):
            should_lock, attempts = security_manager.record_failed_attempt("testuser")
            assert not should_lock
            assert attempts == i + 1

        # 3rd attempt should trigger lock
        should_lock, attempts = security_manager.record_failed_attempt("testuser")
        assert should_lock
        assert attempts == 3

    def test_account_lockout(self):
        """Test account lockout."""
        config = SecurityConfig(max_failed_attempts=3, lockout_duration=2)
        security_manager = SecurityManager(config)

        # Trigger lockout
        for _ in range(3):
            security_manager.record_failed_attempt("testuser")

        # Check locked
        is_locked, seconds = security_manager.is_account_locked("testuser")
        assert is_locked
        assert seconds > 0

        # Wait for unlock
        time.sleep(2.1)
        is_locked, seconds = security_manager.is_account_locked("testuser")
        assert not is_locked

    def test_clear_failed_attempts(self):
        """Test clearing failed attempts."""
        config = SecurityConfig()
        security_manager = SecurityManager(config)

        security_manager.record_failed_attempt("testuser")
        security_manager.clear_failed_attempts("testuser")

        should_lock, attempts = security_manager.record_failed_attempt("testuser")
        assert attempts == 1  # Should restart count

    def test_device_fingerprinting(self):
        """Test device fingerprint generation."""
        security_manager = SecurityManager(SecurityConfig())

        fingerprint = security_manager.generate_device_fingerprint(
            ip_address="192.168.1.1", user_agent="Mozilla/5.0", additional_data={"screen": "1920x1080"}
        )

        assert fingerprint is not None
        assert len(fingerprint) == 64  # SHA256 hex

        # Same data should generate same fingerprint
        fingerprint2 = security_manager.generate_device_fingerprint(
            ip_address="192.168.1.1", user_agent="Mozilla/5.0", additional_data={"screen": "1920x1080"}
        )
        assert fingerprint == fingerprint2

    def test_trusted_device(self):
        """Test trusted device management."""
        security_manager = SecurityManager(SecurityConfig())

        fingerprint = "abc123"
        assert not security_manager.is_trusted_device("user123", fingerprint)

        security_manager.trust_device("user123", fingerprint)
        assert security_manager.is_trusted_device("user123", fingerprint)

    def test_anomaly_detection(self):
        """Test anomaly detection."""
        security_manager = SecurityManager(SecurityConfig(enable_anomaly_detection=True))

        user = User(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            last_login=datetime.utcnow() - timedelta(hours=1),
            failed_login_attempts=2,
        )

        credentials = Credentials(
            username="testuser", password="password", ip_address="192.168.1.1", device_fingerprint="unknown_device"
        )

        is_anomalous, risk_score, reasons = security_manager.detect_anomaly(user, credentials)

        assert risk_score > 0
        assert len(reasons) > 0


# ============================================================================
# User Account Management Tests
# ============================================================================


class TestUserAccountManager:
    """Tests for user account manager."""

    def test_register_user(self):
        """Test user registration."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, errors = manager.register_user(
            username="testuser", email="test@example.com", password="SecurePass123!"
        )

        assert success
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert len(errors) == 0

    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        manager.register_user(username="testuser", email="test1@example.com", password="SecurePass123!")

        success, user, errors = manager.register_user(
            username="testuser", email="test2@example.com", password="SecurePass123!"
        )

        assert not success
        assert any("username" in error.lower() for error in errors)

    def test_register_weak_password(self):
        """Test registration with weak password."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, errors = manager.register_user(username="testuser", email="test@example.com", password="weak")

        assert not success
        assert len(errors) > 0

    def test_get_user_by_various_fields(self):
        """Test retrieving user by different fields."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, _ = manager.register_user(
            username="testuser", email="test@example.com", password="SecurePass123!"
        )

        # By username
        found = manager.get_user("testuser")
        assert found is not None
        assert found.username == "testuser"

        # By user ID
        found = manager.get_user_by_id(user.user_id)
        assert found is not None

        # By email
        found = manager.get_user_by_email("test@example.com")
        assert found is not None

    def test_email_verification(self):
        """Test email verification flow."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, _ = manager.register_user(
            username="testuser", email="test@example.com", password="SecurePass123!"
        )

        assert not user.email_verified

        # Send verification
        code = manager.send_verification_email(user.user_id)
        assert code is not None

        # Verify
        success, error = manager.verify_email(code)
        assert success
        assert user.email_verified

    def test_password_reset_flow(self):
        """Test password reset flow."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        manager.register_user(username="testuser", email="test@example.com", password="OldPass123!")

        # Initiate reset
        token = manager.initiate_password_reset("test@example.com")
        assert token is not None

        # Reset password
        success, errors = manager.reset_password(token, "NewPass456!")
        assert success
        assert len(errors) == 0

        # Verify new password works
        user = manager.get_user("testuser")
        assert hasher.verify_password("NewPass456!", user.password_hash)

    def test_change_password(self):
        """Test password change."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, _ = manager.register_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )

        # Change password
        success, errors = manager.change_password(user.user_id, "OldPass123!", "NewPass456!")
        assert success
        assert len(errors) == 0

        # Verify new password
        user = manager.get_user("testuser")
        assert hasher.verify_password("NewPass456!", user.password_hash)

    def test_change_password_with_wrong_old_password(self):
        """Test password change with wrong old password."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, _ = manager.register_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )

        success, errors = manager.change_password(user.user_id, "WrongPass!", "NewPass456!")
        assert not success
        assert any("invalid" in error.lower() for error in errors)

    def test_activate_deactivate_user(self):
        """Test user activation and deactivation."""
        hasher = PasswordHasher(algorithm=HashAlgorithm.BCRYPT, rounds=4)
        validator = PasswordValidator(PasswordPolicy())
        manager = UserAccountManager(hasher, validator)

        success, user, _ = manager.register_user(
            username="testuser", email="test@example.com", password="SecurePass123!"
        )

        assert user.is_active

        # Deactivate
        manager.deactivate_user(user.user_id)
        assert not user.is_active

        # Activate
        manager.activate_user(user.user_id)
        assert user.is_active


# ============================================================================
# OAuth2 Tests
# ============================================================================


class TestOAuth2Provider:
    """Tests for OAuth2 provider."""

    def test_generate_authorization_url(self):
        """Test OAuth2 authorization URL generation."""
        config = OAuth2Config(
            provider_name="test_provider",
            client_id="client123",
            client_secret="secret123",
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
            scopes=["read", "write"],
        )

        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        provider = OAuth2Provider(config, jwt_manager)

        auth_url = provider.generate_authorization_url(state="state123")

        assert "https://auth.example.com/authorize" in auth_url
        assert "client_id=client123" in auth_url
        assert "state=state123" in auth_url
        assert "scope=read+write" in auth_url

    def test_generate_pkce_pair(self):
        """Test PKCE code verifier and challenge generation."""
        config = OAuth2Config(
            provider_name="test", client_id="id", client_secret="secret", authorization_endpoint="", token_endpoint=""
        )

        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        provider = OAuth2Provider(config, jwt_manager)

        verifier, challenge = provider.generate_pkce_pair()

        assert verifier is not None
        assert challenge is not None
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_create_authorization_code(self):
        """Test authorization code creation."""
        config = OAuth2Config(
            provider_name="test", client_id="id", client_secret="secret", authorization_endpoint="", token_endpoint=""
        )

        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        provider = OAuth2Provider(config, jwt_manager)

        code = provider.create_authorization_code(user_id="user123", scopes=["read"])

        assert code is not None
        assert len(code) > 0

    def test_device_flow_initiation(self):
        """Test device authorization flow initiation."""
        config = OAuth2Config(
            provider_name="test",
            client_id="id",
            client_secret="secret",
            authorization_endpoint="https://auth.example.com",
            token_endpoint="",
        )

        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        provider = OAuth2Provider(config, jwt_manager)

        response = provider.initiate_device_flow()

        assert "device_code" in response
        assert "user_code" in response
        assert "verification_uri" in response
        assert "expires_in" in response

    def test_token_introspection(self):
        """Test token introspection."""
        jwt_manager = JWTManager(secret_key="test_secret", issuer="test_issuer", audience="test_audience")
        config = OAuth2Config(
            provider_name="test", client_id="id", client_secret="secret", authorization_endpoint="", token_endpoint=""
        )

        provider = OAuth2Provider(config, jwt_manager)

        # Generate token
        token = jwt_manager.generate_token(subject="user123", scopes=["read", "write"])

        # Introspect
        result = provider.introspect_token(token)

        assert result["active"]
        assert result["sub"] == "user123"
        assert result["scope"] == "read write"


# ============================================================================
# Main Authentication FSA Tests
# ============================================================================


class TestAuthenticationFSA:
    """Tests for main Authentication FSA."""

    def test_fsa_initialization(self):
        """Test FSA initialization."""
        fsa = AuthenticationFSA()

        assert fsa.current_state == AuthenticationState.UNAUTHENTICATED
        assert fsa.password_hasher is not None
        assert fsa.jwt_manager is not None
        assert fsa.session_manager is not None

    def test_user_registration_via_fsa(self):
        """Test user registration through FSA."""
        fsa = AuthenticationFSA()

        result = fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")

        assert result.success
        assert result.user is not None
        assert result.user.username == "testuser"

    def test_password_authentication(self):
        """Test password-based authentication."""
        fsa = AuthenticationFSA()

        # Register user
        fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")

        # Authenticate
        credentials = Credentials(username="testuser", password="SecurePass123!")
        result = fsa.authenticate(credentials, AuthenticationMethod.PASSWORD)

        assert result.success
        assert result.user is not None
        assert result.access_token is not None
        assert result.state == AuthenticationState.AUTHENTICATED

    def test_failed_authentication(self):
        """Test failed authentication."""
        fsa = AuthenticationFSA()

        fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")

        credentials = Credentials(username="testuser", password="WrongPassword!")
        result = fsa.authenticate(credentials, AuthenticationMethod.PASSWORD)

        assert not result.success
        assert result.access_token is None

    def test_account_lockout_after_failed_attempts(self):
        """Test account lockout after multiple failed attempts."""
        config = SecurityConfig(max_failed_attempts=3, lockout_duration=60)
        fsa = AuthenticationFSA(security_config=config)

        fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")

        # Make 3 failed attempts
        for _ in range(3):
            credentials = Credentials(username="testuser", password="WrongPassword!")
            result = fsa.authenticate(credentials, AuthenticationMethod.PASSWORD)

        # Account should be locked
        assert result.state == AuthenticationState.ACCOUNT_LOCKED

    def test_mfa_required_authentication(self):
        """Test authentication requiring MFA."""
        fsa = AuthenticationFSA()

        # Register and enable MFA
        reg_result = fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")
        user = reg_result.user
        user.mfa_enabled = True

        # Enroll TOTP
        secret, _ = fsa.mfa_manager.enroll_totp(user.user_id)
        enrollment = fsa.mfa_manager.enrollments[user.user_id][0]
        enrollment.verified = True

        # Authenticate (should require MFA)
        credentials = Credentials(username="testuser", password="SecurePass123!")
        result = fsa.authenticate(credentials, AuthenticationMethod.PASSWORD)

        assert not result.success
        assert result.state == AuthenticationState.MFA_REQUIRED
        assert result.mfa_required

    def test_complete_mfa_authentication(self):
        """Test complete authentication with MFA verification."""
        fsa = AuthenticationFSA()

        # Register and enable MFA
        reg_result = fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")
        user = reg_result.user
        user.mfa_enabled = True

        # Enroll TOTP
        secret, _ = fsa.mfa_manager.enroll_totp(user.user_id)
        enrollment = fsa.mfa_manager.enrollments[user.user_id][0]
        enrollment.verified = True

        # Generate MFA challenge
        challenge = fsa.mfa_manager.generate_mfa_challenge(user.user_id, MFAMethod.TOTP)

        # Generate valid TOTP code
        totp = TOTPGenerator()
        code = totp.generate_totp(secret)

        # Update challenge with TOTP (for verification)
        challenge.method = MFAMethod.TOTP

        # Verify MFA
        result = fsa.verify_mfa(user.user_id, challenge.challenge_id, code)

        assert result.success
        assert result.state == AuthenticationState.AUTHENTICATED
        assert result.access_token is not None

    def test_oauth_provider_configuration(self):
        """Test OAuth2 provider configuration."""
        fsa = AuthenticationFSA()

        config = OAuth2Config(
            provider_name="google",
            client_id="google_client_id",
            client_secret="google_secret",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            scopes=["openid", "email", "profile"],
        )

        fsa.configure_oauth_provider("google", config)

        assert "google" in fsa.oauth_providers
        assert fsa.oauth_providers["google"].config.client_id == "google_client_id"

    def test_oauth_flow_initiation(self):
        """Test OAuth2 flow initiation."""
        fsa = AuthenticationFSA()

        config = OAuth2Config(
            provider_name="google",
            client_id="google_client_id",
            client_secret="google_secret",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
        )

        fsa.configure_oauth_provider("google", config)

        success, auth_url, error = fsa.initiate_oauth_flow("google")

        assert success
        assert auth_url is not None
        assert "accounts.google.com" in auth_url
        assert fsa.current_state == AuthenticationState.OAUTH_INITIATED

    def test_logout(self):
        """Test user logout."""
        fsa = AuthenticationFSA()

        # Register and authenticate
        fsa.register_user(username="testuser", email="test@example.com", password="SecurePass123!")
        credentials = Credentials(username="testuser", password="SecurePass123!")
        result = fsa.authenticate(credentials, AuthenticationMethod.PASSWORD)

        session_id = result.session_token

        # Logout
        success = fsa.logout(session_id)

        assert success
        assert fsa.current_state == AuthenticationState.UNAUTHENTICATED

        # Session should be invalid
        is_valid, _, _ = fsa.session_manager.validate_session(session_id)
        assert not is_valid

    def test_state_transitions(self):
        """Test FSA state transitions."""
        fsa = AuthenticationFSA()

        assert fsa.current_state == AuthenticationState.UNAUTHENTICATED
        assert len(fsa.state_history) == 0

        fsa.transition_state(AuthenticationState.AUTHENTICATING)
        assert fsa.current_state == AuthenticationState.AUTHENTICATING
        assert len(fsa.state_history) == 1

        fsa.transition_state(AuthenticationState.AUTHENTICATED)
        assert fsa.current_state == AuthenticationState.AUTHENTICATED
        assert len(fsa.state_history) == 2

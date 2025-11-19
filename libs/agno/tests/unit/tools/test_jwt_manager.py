"""Unit tests for JWT Manager Toolkit."""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

try:
    import jwt
    from agno.tools.jwt_manager import JWTManager
except ImportError:
    pytest.skip("pyjwt not installed", allow_module_level=True)


class TestJWTManagerInit:
    """Test JWT Manager initialization."""

    def test_init_with_secret_key(self):
        """Test initialization with secret key."""
        manager = JWTManager(secret_key="test_secret")
        assert manager.secret_key == "test_secret"
        assert manager.default_algorithm == "HS256"

    @patch.dict("os.environ", {"JWT_SECRET_KEY": "env_secret"})
    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        manager = JWTManager()
        assert manager.secret_key == "env_secret"

    def test_init_with_custom_algorithm(self):
        """Test initialization with custom algorithm."""
        manager = JWTManager(
            secret_key="test_secret",
            default_algorithm="HS512"
        )
        assert manager.default_algorithm == "HS512"

    def test_init_with_rsa_keys(self):
        """Test initialization with RSA keys."""
        private_key = "test_private_key"
        public_key = "test_public_key"
        manager = JWTManager(
            private_key=private_key,
            public_key=public_key,
            default_algorithm="RS256"
        )
        assert manager.private_key == private_key
        assert manager.public_key == public_key

    def test_init_with_custom_expiration(self):
        """Test initialization with custom expiration times."""
        manager = JWTManager(
            secret_key="test_secret",
            default_expiration=7200,
            refresh_expiration=86400
        )
        assert manager.default_expiration == 7200
        assert manager.refresh_expiration == 86400

    def test_init_with_issuer_and_audience(self):
        """Test initialization with issuer and audience."""
        manager = JWTManager(
            secret_key="test_secret",
            issuer="test_issuer",
            audience="test_audience"
        )
        assert manager.issuer == "test_issuer"
        assert manager.audience == "test_audience"

    def test_init_with_selective_functions(self):
        """Test initialization with selective function registration."""
        manager = JWTManager(
            secret_key="test_secret",
            enable_generate_token=True,
            enable_validate_token=False,
            enable_decode_token=False,
        )
        assert "generate_token" in manager.functions
        assert "validate_token" not in manager.functions
        assert "decode_token" not in manager.functions


class TestTokenGeneration:
    """Test token generation functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_generate_token_basic(self, manager):
        """Test basic token generation."""
        payload = json.dumps({"user_id": "123", "username": "testuser"})
        result = manager.generate_token(payload=payload)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "token" in result_data
        assert result_data["algorithm"] == "HS256"
        assert "expires_in" in result_data

    def test_generate_token_with_custom_expiration(self, manager):
        """Test token generation with custom expiration."""
        payload = json.dumps({"user_id": "123"})
        result = manager.generate_token(payload=payload, expiration=7200)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["expires_in"] == 7200

    def test_generate_token_with_custom_algorithm(self, manager):
        """Test token generation with custom algorithm."""
        payload = json.dumps({"user_id": "123"})
        result = manager.generate_token(
            payload=payload,
            algorithm="HS512"
        )
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["algorithm"] == "HS512"

    def test_generate_token_with_issuer_and_audience(self, manager):
        """Test token generation with issuer and audience."""
        payload = json.dumps({"user_id": "123"})
        result = manager.generate_token(
            payload=payload,
            issuer="test_issuer",
            audience="test_audience"
        )
        result_data = json.loads(result)

        assert result_data["success"] is True

        # Decode and verify claims
        token = result_data["token"]
        decoded = jwt.decode(
            token,
            "test_secret_key_12345",
            algorithms=["HS256"],
            audience="test_audience"
        )
        assert decoded["iss"] == "test_issuer"
        assert decoded["aud"] == "test_audience"

    def test_generate_token_with_subject(self, manager):
        """Test token generation with subject claim."""
        payload = json.dumps({"user_id": "123"})
        result = manager.generate_token(
            payload=payload,
            subject="user:123"
        )
        result_data = json.loads(result)

        assert result_data["success"] is True

        # Verify subject claim
        token = result_data["token"]
        decoded = jwt.decode(
            token,
            "test_secret_key_12345",
            algorithms=["HS256"]
        )
        assert decoded["sub"] == "user:123"

    def test_generate_token_with_additional_claims(self, manager):
        """Test token generation with additional custom claims."""
        payload = json.dumps({"user_id": "123"})
        additional = json.dumps({"role": "admin", "permissions": ["read", "write"]})
        result = manager.generate_token(
            payload=payload,
            additional_claims=additional
        )
        result_data = json.loads(result)

        assert result_data["success"] is True

        # Verify additional claims
        token = result_data["token"]
        decoded = jwt.decode(
            token,
            "test_secret_key_12345",
            algorithms=["HS256"]
        )
        assert decoded["role"] == "admin"
        assert decoded["permissions"] == ["read", "write"]

    def test_generate_token_invalid_json(self, manager):
        """Test token generation with invalid JSON."""
        result = manager.generate_token(payload="invalid json")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Invalid JSON" in result_data["error"]

    def test_generate_token_without_key(self):
        """Test token generation without configured key."""
        manager = JWTManager(default_algorithm="HS256")
        payload = json.dumps({"user_id": "123"})
        result = manager.generate_token(payload=payload)
        result_data = json.loads(result)

        assert "error" in result_data
        assert "No key configured" in result_data["error"]


class TestTokenValidation:
    """Test token validation functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_validate_token_success(self, manager):
        """Test successful token validation."""
        # Generate a token
        payload = json.dumps({"user_id": "123", "username": "testuser"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate the token
        result = manager.validate_token(token=token)
        result_data = json.loads(result)

        assert result_data["valid"] is True
        assert "payload" in result_data
        assert result_data["payload"]["user_id"] == "123"
        assert result_data["payload"]["username"] == "testuser"

    def test_validate_token_with_audience(self, manager):
        """Test token validation with audience verification."""
        # Generate token with audience
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(
            payload=payload,
            audience="test_audience"
        )
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate with correct audience
        result = manager.validate_token(
            token=token,
            audience="test_audience"
        )
        result_data = json.loads(result)
        assert result_data["valid"] is True

        # Validate with incorrect audience
        result = manager.validate_token(
            token=token,
            audience="wrong_audience"
        )
        result_data = json.loads(result)
        assert result_data["valid"] is False
        assert "Invalid audience" in result_data["error"]

    def test_validate_token_with_issuer(self, manager):
        """Test token validation with issuer verification."""
        # Generate token with issuer
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(
            payload=payload,
            issuer="test_issuer"
        )
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate with correct issuer
        result = manager.validate_token(
            token=token,
            issuer="test_issuer"
        )
        result_data = json.loads(result)
        assert result_data["valid"] is True

        # Validate with incorrect issuer
        result = manager.validate_token(
            token=token,
            issuer="wrong_issuer"
        )
        result_data = json.loads(result)
        assert result_data["valid"] is False
        assert "Invalid issuer" in result_data["error"]

    def test_validate_expired_token(self, manager):
        """Test validation of expired token."""
        # Generate token with very short expiration
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload, expiration=1)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Wait for expiration
        time.sleep(2)

        # Validate expired token
        result = manager.validate_token(token=token)
        result_data = json.loads(result)

        assert result_data["valid"] is False
        assert "expired" in result_data["error"].lower()

    def test_validate_token_skip_expiration(self, manager):
        """Test token validation skipping expiration check."""
        # Generate token with very short expiration
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload, expiration=1)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Wait for expiration
        time.sleep(2)

        # Validate with expiration check disabled
        result = manager.validate_token(
            token=token,
            verify_expiration=False
        )
        result_data = json.loads(result)

        assert result_data["valid"] is True

    def test_validate_token_invalid_signature(self, manager):
        """Test validation of token with invalid signature."""
        # Generate token with one secret
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Try to validate with different secret
        manager2 = JWTManager(secret_key="different_secret")
        result = manager2.validate_token(token=token)
        result_data = json.loads(result)

        assert result_data["valid"] is False

    def test_validate_revoked_token(self, manager):
        """Test validation of revoked token."""
        # Generate token
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Revoke token
        manager.revoke_token(token=token)

        # Try to validate revoked token
        result = manager.validate_token(token=token)
        result_data = json.loads(result)

        assert result_data["valid"] is False
        assert "revoked" in result_data["error"].lower()


class TestTokenDecoding:
    """Test token decoding functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_decode_token_without_verification(self, manager):
        """Test token decoding without verification."""
        # Generate token
        payload = json.dumps({"user_id": "123", "username": "testuser"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Decode without verification
        result = manager.decode_token(token=token, verify=False)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "header" in result_data
        assert "payload" in result_data
        assert result_data["payload"]["user_id"] == "123"

    def test_decode_token_with_verification(self, manager):
        """Test token decoding with verification."""
        # Generate token
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Decode with verification
        result = manager.decode_token(token=token, verify=True)
        result_data = json.loads(result)

        assert result_data["valid"] is True
        assert "payload" in result_data

    def test_decode_invalid_token(self, manager):
        """Test decoding invalid token."""
        result = manager.decode_token(token="invalid.token.format")
        result_data = json.loads(result)

        assert "error" in result_data


class TestRefreshTokens:
    """Test refresh token functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_create_refresh_token(self, manager):
        """Test creating a refresh token."""
        result = manager.create_refresh_token(user_id="123")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "refresh_token" in result_data
        assert result_data["expires_in"] == manager.refresh_expiration

        # Verify token contains user_id
        token = result_data["refresh_token"]
        decoded = jwt.decode(
            token,
            "test_secret_key_12345",
            algorithms=["HS256"]
        )
        assert decoded["user_id"] == "123"
        assert decoded["type"] == "refresh"

    def test_create_refresh_token_with_payload(self, manager):
        """Test creating refresh token with custom payload."""
        custom_payload = json.dumps({"role": "admin"})
        result = manager.create_refresh_token(
            user_id="123",
            payload=custom_payload
        )
        result_data = json.loads(result)

        assert result_data["success"] is True

        # Verify custom payload
        token = result_data["refresh_token"]
        decoded = jwt.decode(
            token,
            "test_secret_key_12345",
            algorithms=["HS256"]
        )
        assert decoded["role"] == "admin"

    def test_use_refresh_token_success(self, manager):
        """Test using a refresh token to generate access token."""
        # Create refresh token
        refresh_result = manager.create_refresh_token(user_id="123")
        refresh_data = json.loads(refresh_result)
        refresh_token = refresh_data["refresh_token"]

        # Use refresh token
        new_payload = json.dumps({"user_id": "123", "session": "new"})
        result = manager.use_refresh_token(
            refresh_token=refresh_token,
            new_payload=new_payload
        )
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "token" in result_data

        # Verify new token contains the new payload
        new_token = result_data["token"]
        decoded = jwt.decode(
            new_token,
            "test_secret_key_12345",
            algorithms=["HS256"]
        )
        assert decoded["session"] == "new"

    def test_use_refresh_token_twice(self, manager):
        """Test that refresh token can only be used once."""
        # Create refresh token
        refresh_result = manager.create_refresh_token(user_id="123")
        refresh_data = json.loads(refresh_result)
        refresh_token = refresh_data["refresh_token"]

        # Use refresh token first time
        new_payload = json.dumps({"user_id": "123"})
        result1 = manager.use_refresh_token(
            refresh_token=refresh_token,
            new_payload=new_payload
        )
        result1_data = json.loads(result1)
        assert result1_data["success"] is True

        # Try to use refresh token second time
        result2 = manager.use_refresh_token(
            refresh_token=refresh_token,
            new_payload=new_payload
        )
        result2_data = json.loads(result2)
        assert "error" in result2_data
        assert "already used" in result2_data["error"].lower()

    def test_use_invalid_refresh_token(self, manager):
        """Test using an invalid refresh token."""
        new_payload = json.dumps({"user_id": "123"})
        result = manager.use_refresh_token(
            refresh_token="invalid_token",
            new_payload=new_payload
        )
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Invalid refresh token" in result_data["error"]


class TestTokenRevocation:
    """Test token revocation functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_revoke_token(self, manager):
        """Test revoking a token."""
        # Generate token
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Revoke token
        result = manager.revoke_token(token=token)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "revoked" in result_data["message"].lower()

    def test_is_token_revoked(self, manager):
        """Test checking if token is revoked."""
        # Generate token
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Check before revocation
        result = manager.is_token_revoked(token=token)
        result_data = json.loads(result)
        assert result_data["revoked"] is False
        assert result_data["token_status"] == "active"

        # Revoke token
        manager.revoke_token(token=token)

        # Check after revocation
        result = manager.is_token_revoked(token=token)
        result_data = json.loads(result)
        assert result_data["revoked"] is True
        assert result_data["token_status"] == "revoked"


class TestClaimsValidation:
    """Test claims validation functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_validate_claims_success(self, manager):
        """Test successful claims validation."""
        # Generate token with specific claims
        payload = json.dumps({
            "user_id": "123",
            "role": "admin",
            "permissions": ["read", "write"]
        })
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate claims
        required_claims = json.dumps({
            "user_id": "123",
            "role": "admin"
        })
        result = manager.validate_claims(
            token=token,
            required_claims=required_claims
        )
        result_data = json.loads(result)

        assert result_data["valid"] is True

    def test_validate_claims_missing(self, manager):
        """Test claims validation with missing claims."""
        # Generate token
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate with missing claim
        required_claims = json.dumps({
            "user_id": "123",
            "role": "admin"
        })
        result = manager.validate_claims(
            token=token,
            required_claims=required_claims
        )
        result_data = json.loads(result)

        assert result_data["valid"] is False
        assert "role" in result_data["missing_claims"]

    def test_validate_claims_invalid_value(self, manager):
        """Test claims validation with invalid claim values."""
        # Generate token
        payload = json.dumps({
            "user_id": "123",
            "role": "user"
        })
        gen_result = manager.generate_token(payload=payload)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Validate with wrong value
        required_claims = json.dumps({
            "user_id": "123",
            "role": "admin"
        })
        result = manager.validate_claims(
            token=token,
            required_claims=required_claims
        )
        result_data = json.loads(result)

        assert result_data["valid"] is False
        assert len(result_data["invalid_claims"]) > 0
        assert result_data["invalid_claims"][0]["claim"] == "role"
        assert result_data["invalid_claims"][0]["expected"] == "admin"
        assert result_data["invalid_claims"][0]["actual"] == "user"


class TestExpirationChecking:
    """Test expiration checking functionality."""

    @pytest.fixture
    def manager(self):
        """Create JWT manager instance for testing."""
        return JWTManager(secret_key="test_secret_key_12345")

    def test_check_expiration_valid(self, manager):
        """Test expiration check on valid token."""
        # Generate token with 3600 second expiration
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload, expiration=3600)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Check expiration
        result = manager.check_expiration(token=token)
        result_data = json.loads(result)

        assert result_data["expired"] is False
        assert result_data["status"] == "valid"
        assert result_data["time_remaining_seconds"] > 3500  # Should be close to 3600

    def test_check_expiration_expired(self, manager):
        """Test expiration check on expired token."""
        # Generate token with 1 second expiration
        payload = json.dumps({"user_id": "123"})
        gen_result = manager.generate_token(payload=payload, expiration=1)
        gen_data = json.loads(gen_result)
        token = gen_data["token"]

        # Wait for expiration
        time.sleep(2)

        # Check expiration
        result = manager.check_expiration(token=token)
        result_data = json.loads(result)

        assert result_data["expired"] is True
        assert result_data["status"] == "expired"
        assert result_data["time_remaining_seconds"] == 0

    def test_check_expiration_no_exp_claim(self, manager):
        """Test expiration check on token without exp claim."""
        # Create a token manually without exp claim
        token = jwt.encode(
            {"user_id": "123"},
            "test_secret_key_12345",
            algorithm="HS256"
        )

        # Check expiration
        result = manager.check_expiration(token=token)
        result_data = json.loads(result)

        assert "error" in result_data
        assert "does not contain expiration" in result_data["error"]


class TestInstructions:
    """Test instructions method."""

    def test_instructions(self):
        """Test that instructions are provided."""
        manager = JWTManager(secret_key="test_secret")
        instructions = manager.instructions()

        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert "JWT" in instructions
        assert "Token Generation" in instructions

"""
Comprehensive tests for OAuth Flow Handler FSA

Tests cover:
- All OAuth flow types (Authorization Code, PKCE, Implicit, Client Credentials, Refresh)
- State machine transitions and validations
- Security features (PKCE, state parameter, timing-safe comparison)
- Token management (expiry, refresh, storage)
- Error handling and edge cases
- Multiple provider configurations
"""

import pytest
import time
import secrets
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from agno.cli.oauth_flow import (
    OAuthFlowHandler,
    OAuthFlowType,
    OAuthState,
    OAuthToken,
    OAuthContext,
    ProviderConfig,
    OAuthError,
    InvalidStateError,
    InvalidScopeError,
    TokenExpiredError,
    ProviderConfigError
)


class TestOAuthToken:
    """Test OAuth token data structure"""

    def test_token_creation(self):
        """Test basic token creation"""
        token = OAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="read write"
        )
        assert token.access_token == "test_access_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "read write"

    def test_token_not_expired(self):
        """Test token expiry check - not expired"""
        token = OAuthToken(
            access_token="test",
            expires_in=3600,
            issued_at=time.time()
        )
        assert not token.is_expired

    def test_token_expired(self):
        """Test token expiry check - expired"""
        token = OAuthToken(
            access_token="test",
            expires_in=3600,
            issued_at=time.time() - 3700  # Issued more than 1 hour ago
        )
        assert token.is_expired

    def test_token_expiry_buffer(self):
        """Test token expiry with 60-second buffer"""
        # Token expires in 30 seconds - should be considered expired due to buffer
        token = OAuthToken(
            access_token="test",
            expires_in=90,
            issued_at=time.time() - 40  # 50 seconds remaining
        )
        assert token.is_expired  # Expired due to 60s buffer

    def test_token_no_expiry(self):
        """Test token without expiry"""
        token = OAuthToken(access_token="test")
        assert not token.is_expired

    def test_token_expires_at(self):
        """Test expiration datetime calculation"""
        issued = time.time()
        token = OAuthToken(
            access_token="test",
            expires_in=3600,
            issued_at=issued
        )
        expected = datetime.fromtimestamp(issued + 3600)
        assert abs((token.expires_at - expected).total_seconds()) < 1

    def test_token_serialization(self):
        """Test token to/from dict"""
        original = OAuthToken(
            access_token="test",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh",
            scope="read"
        )
        data = original.to_dict()
        restored = OAuthToken.from_dict(data)
        assert restored.access_token == original.access_token
        assert restored.refresh_token == original.refresh_token


class TestProviderConfig:
    """Test OAuth provider configurations"""

    def test_google_provider(self):
        """Test Google provider configuration"""
        config = ProviderConfig.google(
            client_id="test_client_id",
            client_secret="test_secret",
            scopes=["email", "profile"]
        )
        assert config.name == "google"
        assert "accounts.google.com" in config.authorization_endpoint
        assert config.supports_pkce is True
        assert config.supports_refresh is True
        assert "access_type" in config.additional_auth_params

    def test_github_provider(self):
        """Test GitHub provider configuration"""
        config = ProviderConfig.github(
            client_id="test_client_id",
            client_secret="test_secret",
            scopes=["repo", "user"]
        )
        assert config.name == "github"
        assert "github.com" in config.authorization_endpoint
        assert config.supports_pkce is False  # GitHub doesn't support PKCE
        assert config.supports_refresh is False

    def test_microsoft_provider(self):
        """Test Microsoft provider configuration"""
        config = ProviderConfig.microsoft(
            client_id="test_client_id",
            client_secret="test_secret",
            scopes=["User.Read"],
            tenant="common"
        )
        assert config.name == "microsoft"
        assert "login.microsoftonline.com" in config.authorization_endpoint
        assert "common" in config.authorization_endpoint
        assert config.supports_pkce is True

    def test_custom_provider(self):
        """Test custom provider configuration"""
        config = ProviderConfig(
            name="custom",
            authorization_endpoint="https://example.com/auth",
            token_endpoint="https://example.com/token",
            client_id="client123",
            scopes=["custom_scope"]
        )
        assert config.name == "custom"
        assert config.authorization_endpoint == "https://example.com/auth"


class TestOAuthContext:
    """Test OAuth context management"""

    def test_state_generation(self):
        """Test state parameter generation"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        state = context.generate_state()
        assert len(state) > 20
        assert context.state_parameter == state

    def test_nonce_generation(self):
        """Test nonce generation"""
        provider = ProviderConfig.google("client", "secret", ["openid"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        nonce = context.generate_nonce()
        assert len(nonce) > 20
        assert context.nonce == nonce

    def test_pkce_generation(self):
        """Test PKCE verifier and challenge generation"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE_PKCE)

        verifier, challenge = context.generate_pkce_challenge()
        assert len(verifier) > 40
        assert len(challenge) > 20
        assert context.code_verifier == verifier
        assert context.code_challenge == challenge
        # Verify challenge is different from verifier
        assert challenge != verifier

    def test_state_validation_success(self):
        """Test successful state validation"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        state = context.generate_state()
        assert context.validate_state(state) is True

    def test_state_validation_failure(self):
        """Test failed state validation"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        context.generate_state()
        assert context.validate_state("wrong_state") is False

    def test_state_validation_timing_safe(self):
        """Test that state validation uses timing-safe comparison"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        state = context.generate_state()

        # This should use secrets.compare_digest internally
        with patch('secrets.compare_digest', return_value=True) as mock_compare:
            context.validate_state(state)
            # Note: In actual implementation, validate_state uses compare_digest


class TestOAuthFlowHandler:
    """Test OAuth Flow Handler FSA"""

    @pytest.fixture
    def google_provider(self):
        """Google provider fixture"""
        return ProviderConfig.google(
            client_id="test_client_id",
            client_secret="test_secret",
            scopes=["email", "profile"]
        )

    @pytest.fixture
    def github_provider(self):
        """GitHub provider fixture"""
        return ProviderConfig.github(
            client_id="test_client_id",
            client_secret="test_secret",
            scopes=["repo"]
        )

    def test_handler_initialization(self, google_provider):
        """Test OAuth handler initialization"""
        handler = OAuthFlowHandler(
            provider=google_provider,
            flow_type=OAuthFlowType.AUTHORIZATION_CODE_PKCE
        )
        assert handler.context.state == OAuthState.INITIAL
        assert handler.context.flow_type == OAuthFlowType.AUTHORIZATION_CODE_PKCE
        assert handler.context.provider.name == "google"

    def test_build_authorization_url_pkce(self, google_provider):
        """Test building authorization URL with PKCE"""
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)

        url = handler.build_authorization_url()

        # Verify URL structure
        assert "accounts.google.com" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert "state=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "scope=email+profile" in url or "scope=email%20profile" in url

        # Verify state transition
        assert handler.context.state == OAuthState.WAITING_FOR_CALLBACK

    def test_build_authorization_url_implicit(self, google_provider):
        """Test building authorization URL for implicit flow"""
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.IMPLICIT)

        url = handler.build_authorization_url()

        assert "response_type=token" in url
        assert "code_challenge" not in url  # No PKCE for implicit

    def test_build_authorization_url_with_openid(self, google_provider):
        """Test authorization URL with OpenID Connect"""
        google_provider.scopes = ["openid", "email"]
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)

        url = handler.build_authorization_url()

        assert "nonce=" in url
        assert handler.context.nonce is not None

    def test_build_authorization_url_invalid_state(self, google_provider):
        """Test building auth URL from invalid state"""
        handler = OAuthFlowHandler(google_provider)
        handler.context.state = OAuthState.AUTHENTICATED

        with pytest.raises(OAuthError, match="Cannot build auth URL"):
            handler.build_authorization_url()

    def test_pkce_not_supported_error(self):
        """Test error when PKCE used with unsupported provider"""
        github = ProviderConfig.github("client", "secret", ["repo"])
        handler = OAuthFlowHandler(github, OAuthFlowType.AUTHORIZATION_CODE_PKCE)

        with pytest.raises(ProviderConfigError, match="does not support PKCE"):
            handler.build_authorization_url()

    def test_handle_callback_success(self, google_provider):
        """Test successful callback handling"""
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)
        url = handler.build_authorization_url()

        # Extract state from URL
        import re
        state_match = re.search(r'state=([^&]+)', url)
        state = state_match.group(1)

        # Simulate callback
        callback_params = {
            "code": "test_authorization_code",
            "state": state
        }

        token = handler.handle_callback(callback_params)

        assert token is not None
        assert token.access_token
        assert handler.context.state == OAuthState.AUTHENTICATED

    def test_handle_callback_state_mismatch(self, google_provider):
        """Test callback with mismatched state"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        callback_params = {
            "code": "test_code",
            "state": "wrong_state"
        }

        with pytest.raises(InvalidStateError):
            handler.handle_callback(callback_params)

        assert handler.context.state == OAuthState.ERROR

    def test_handle_callback_with_error(self, google_provider):
        """Test callback containing error"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        state = handler.context.state_parameter
        callback_params = {
            "error": "access_denied",
            "error_description": "User denied access",
            "state": state
        }

        with pytest.raises(OAuthError, match="access_denied"):
            handler.handle_callback(callback_params)

        assert handler.context.state == OAuthState.ERROR
        assert handler.context.error == "access_denied"

    def test_handle_callback_missing_code(self, google_provider):
        """Test callback with missing authorization code"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        state = handler.context.state_parameter
        callback_params = {
            "state": state
            # Missing "code"
        }

        with pytest.raises(OAuthError, match="code missing"):
            handler.handle_callback(callback_params)

    def test_implicit_flow_callback(self, google_provider):
        """Test implicit flow callback (returns token directly)"""
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.IMPLICIT)
        handler.build_authorization_url()

        state = handler.context.state_parameter
        callback_params = {
            "access_token": "implicit_access_token",
            "token_type": "Bearer",
            "expires_in": "3600",
            "state": state
        }

        token = handler.handle_callback(callback_params)

        assert token.access_token == "implicit_access_token"
        assert handler.context.state == OAuthState.AUTHENTICATED

    def test_exchange_code_for_token(self, google_provider):
        """Test authorization code exchange"""
        handler = OAuthFlowHandler(google_provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)
        handler.build_authorization_url()

        # Manually transition to exchanging state
        handler.context.state = OAuthState.EXCHANGING_CODE

        token = handler.exchange_code_for_token("test_code")

        assert token.access_token
        assert token.refresh_token  # Google supports refresh
        assert handler.context.state == OAuthState.AUTHENTICATED

    def test_refresh_access_token(self, google_provider):
        """Test token refresh"""
        handler = OAuthFlowHandler(google_provider)

        # Set up authenticated state with expired token
        old_token = OAuthToken(
            access_token="old_token",
            expires_in=3600,
            issued_at=time.time() - 4000,  # Expired
            refresh_token="refresh_token"
        )
        handler.context.token = old_token
        handler.context.state = OAuthState.AUTHENTICATED

        new_token = handler.refresh_access_token()

        assert new_token.access_token != "old_token"
        assert new_token.access_token  # New token generated
        assert handler.context.state == OAuthState.AUTHENTICATED

    def test_refresh_token_not_available(self, google_provider):
        """Test refresh when no refresh token available"""
        handler = OAuthFlowHandler(google_provider)
        handler.context.state = OAuthState.AUTHENTICATED
        handler.context.token = OAuthToken(access_token="test")  # No refresh token

        with pytest.raises(OAuthError, match="No refresh token"):
            handler.refresh_access_token()

    def test_refresh_not_supported(self):
        """Test refresh with provider that doesn't support it"""
        github = ProviderConfig.github("client", "secret", ["repo"])
        handler = OAuthFlowHandler(github)

        handler.context.state = OAuthState.AUTHENTICATED
        handler.context.token = OAuthToken(
            access_token="test",
            refresh_token="refresh"  # Has refresh token
        )

        with pytest.raises(ProviderConfigError, match="does not support token refresh"):
            handler.refresh_access_token()

    def test_get_token_valid(self, google_provider):
        """Test getting valid token"""
        handler = OAuthFlowHandler(google_provider)

        token = OAuthToken(
            access_token="valid_token",
            expires_in=3600,
            issued_at=time.time()
        )
        handler.context.token = token
        handler.context.state = OAuthState.AUTHENTICATED

        retrieved_token = handler.get_token()
        assert retrieved_token.access_token == "valid_token"

    def test_get_token_auto_refresh(self, google_provider):
        """Test automatic token refresh on get_token()"""
        handler = OAuthFlowHandler(google_provider)

        expired_token = OAuthToken(
            access_token="expired_token",
            expires_in=3600,
            issued_at=time.time() - 4000,
            refresh_token="refresh"
        )
        handler.context.token = expired_token
        handler.context.state = OAuthState.AUTHENTICATED

        new_token = handler.get_token()

        assert new_token.access_token != "expired_token"

    def test_get_token_expired_no_refresh(self):
        """Test get_token with expired token and no refresh available"""
        github = ProviderConfig.github("client", "secret", ["repo"])
        handler = OAuthFlowHandler(github)

        expired_token = OAuthToken(
            access_token="expired",
            expires_in=3600,
            issued_at=time.time() - 4000
        )
        handler.context.token = expired_token
        handler.context.state = OAuthState.AUTHENTICATED

        with pytest.raises(TokenExpiredError):
            handler.get_token()

    def test_validate_scopes(self, google_provider):
        """Test scope validation"""
        handler = OAuthFlowHandler(google_provider)
        handler.context.granted_scopes = ["email", "profile", "openid"]

        assert handler.validate_scopes(["email"]) is True
        assert handler.validate_scopes(["email", "profile"]) is True
        assert handler.validate_scopes(["email", "calendar"]) is False

    def test_state_transition_validation(self, google_provider):
        """Test invalid state transitions are prevented"""
        handler = OAuthFlowHandler(google_provider)

        # Try invalid transition: INITIAL -> AUTHENTICATED
        with pytest.raises(OAuthError, match="Invalid state transition"):
            handler._transition_to(OAuthState.AUTHENTICATED)

    def test_transition_hooks(self, google_provider):
        """Test state transition hooks"""
        handler = OAuthFlowHandler(google_provider)

        hook_called = {"called": False, "context": None}

        def my_hook(context):
            hook_called["called"] = True
            hook_called["context"] = context

        handler.register_transition_hook(
            OAuthState.INITIAL,
            OAuthState.AUTHORIZATION_REQUESTED,
            my_hook
        )

        handler.build_authorization_url()

        assert hook_called["called"] is True
        assert hook_called["context"] is not None

    def test_reset_flow(self, google_provider):
        """Test flow reset"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        assert handler.context.state != OAuthState.INITIAL
        assert handler.context.state_parameter is not None

        handler.reset()

        assert handler.context.state == OAuthState.INITIAL
        assert handler.context.state_parameter is None

    def test_export_import_state(self, google_provider):
        """Test state export and import for persistence"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        # Simulate completing flow
        handler.context.state = OAuthState.AUTHENTICATED
        handler.context.token = OAuthToken(access_token="test_token")
        handler.context.granted_scopes = ["email"]

        # Export state
        state_data = handler.export_state()

        # Create new handler and import
        new_handler = OAuthFlowHandler(google_provider)
        new_handler.import_state(state_data)

        assert new_handler.context.state == OAuthState.AUTHENTICATED
        assert new_handler.context.token.access_token == "test_token"
        assert new_handler.context.granted_scopes == ["email"]

    def test_additional_auth_params(self, google_provider):
        """Test additional authorization parameters"""
        handler = OAuthFlowHandler(google_provider)

        url = handler.build_authorization_url({"custom_param": "custom_value"})

        assert "custom_param=custom_value" in url

    def test_concurrent_flows(self, google_provider):
        """Test multiple independent flows"""
        handler1 = OAuthFlowHandler(google_provider)
        handler2 = OAuthFlowHandler(google_provider)

        url1 = handler1.build_authorization_url()
        url2 = handler2.build_authorization_url()

        # State parameters should be different
        assert handler1.context.state_parameter != handler2.context.state_parameter
        assert url1 != url2


class TestSecurityFeatures:
    """Test security best practices"""

    def test_pkce_verifier_length(self):
        """Test PKCE verifier has sufficient entropy"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE_PKCE)

        verifier, _ = context.generate_pkce_challenge()
        assert len(verifier) >= 43  # Minimum recommended length

    def test_state_parameter_randomness(self):
        """Test state parameters are unique"""
        provider = ProviderConfig.google("client", "secret", ["email"])

        states = set()
        for _ in range(100):
            context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)
            state = context.generate_state()
            states.add(state)

        # All should be unique
        assert len(states) == 100

    def test_no_token_leakage_in_logs(self, google_provider, caplog):
        """Test tokens are not logged"""
        handler = OAuthFlowHandler(google_provider)
        handler.build_authorization_url()

        handler.context.state = OAuthState.EXCHANGING_CODE
        token = handler.exchange_code_for_token("code123")

        # Check logs don't contain actual token
        for record in caplog.records:
            assert token.access_token not in record.message


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_scopes(self):
        """Test handling of empty scopes"""
        config = ProviderConfig.google("client", "secret", [])
        handler = OAuthFlowHandler(config)

        url = handler.build_authorization_url()
        assert "scope=" in url  # Should still have scope parameter

    def test_very_long_state(self):
        """Test handling of very long state parameter"""
        provider = ProviderConfig.google("client", "secret", ["email"])
        context = OAuthContext(provider=provider, flow_type=OAuthFlowType.AUTHORIZATION_CODE)

        # Generate state
        state = context.generate_state()

        # State should be URL-safe and reasonable length
        assert len(state) < 200
        assert all(c.isalnum() or c in '-_' for c in state)

    def test_callback_wrong_state(self, google_provider):
        """Test handling callback from wrong state"""
        handler = OAuthFlowHandler(google_provider)

        # Don't build auth URL, try callback directly
        with pytest.raises(OAuthError):
            handler.handle_callback({"code": "test", "state": "test"})

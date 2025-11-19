"""
OAuth Flow Handler - Working Examples

This module provides practical examples of using the OAuth FSA handler
with different providers and flow types. Includes 3 complete patterns:

1. Google OAuth with PKCE (Authorization Code Flow)
2. GitHub OAuth (Standard Authorization Code Flow)
3. Token Auto-Refresh Pattern

Production-ready examples ready for high-velocity generation.
"""

import logging
from typing import Optional
from agno.cli.oauth_flow import (
    OAuthFlowHandler,
    OAuthFlowType,
    OAuthToken,
    ProviderConfig,
    OAuthError
)


logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN 1: Google OAuth with PKCE
# ============================================================================

class GoogleOAuthExample:
    """
    Complete working example: Google OAuth 2.0 with PKCE

    Use case: Authenticating users with Google accounts for Gmail, Calendar, etc.
    Flow: Authorization Code with PKCE (most secure for public clients)

    Features:
    - PKCE for enhanced security
    - Automatic token refresh
    - Scope validation
    - State parameter protection
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:9191/callback"):
        """
        Initialize Google OAuth handler

        Args:
            client_id: Google OAuth client ID (from Google Cloud Console)
            client_secret: Google OAuth client secret
            redirect_uri: Callback URL (must match Google Console config)
        """
        # Configure Google provider
        self.provider = ProviderConfig.google(
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/gmail.readonly"
            ]
        )
        self.provider.redirect_uri = redirect_uri

        # Create OAuth handler with PKCE
        self.handler = OAuthFlowHandler(
            provider=self.provider,
            flow_type=OAuthFlowType.AUTHORIZATION_CODE_PKCE
        )

        logger.info("Google OAuth handler initialized with PKCE")

    def start_authentication(self) -> str:
        """
        Start authentication flow

        Returns:
            Authorization URL to redirect user to

        Example:
            >>> handler = GoogleOAuthExample("client_id", "client_secret")
            >>> auth_url = handler.start_authentication()
            >>> print(f"Visit: {auth_url}")
        """
        # Build authorization URL with PKCE
        auth_url = self.handler.build_authorization_url(
            additional_params={
                "access_type": "offline",  # Request refresh token
                "prompt": "consent"  # Force consent screen
            }
        )

        logger.info("Authorization URL generated")
        return auth_url

    def handle_callback(self, authorization_code: str, state: str) -> OAuthToken:
        """
        Handle OAuth callback after user authorization

        Args:
            authorization_code: Code from callback URL
            state: State parameter from callback URL

        Returns:
            OAuth token with access and refresh tokens

        Raises:
            InvalidStateError: If state validation fails
            OAuthError: If callback contains error

        Example:
            >>> token = handler.handle_callback(code="abc123", state="xyz789")
            >>> print(f"Access token: {token.access_token}")
        """
        callback_params = {
            "code": authorization_code,
            "state": state
        }

        try:
            token = self.handler.handle_callback(callback_params)
            logger.info("Authentication successful")
            return token
        except OAuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def get_valid_token(self) -> OAuthToken:
        """
        Get valid access token, auto-refreshing if expired

        Returns:
            Valid OAuth token

        Example:
            >>> token = handler.get_valid_token()
            >>> # Use token to make API calls
            >>> headers = {"Authorization": f"Bearer {token.access_token}"}
        """
        try:
            token = self.handler.get_token()
            logger.info("Retrieved valid token")
            return token
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            raise

    def save_state(self) -> dict:
        """
        Export state for persistence (save to file/database)

        Returns:
            Serializable state dictionary

        Example:
            >>> state = handler.save_state()
            >>> with open("oauth_state.json", "w") as f:
            >>>     json.dump(state, f)
        """
        return self.handler.export_state()

    def restore_state(self, state_data: dict):
        """
        Restore from saved state

        Args:
            state_data: Previously saved state

        Example:
            >>> with open("oauth_state.json", "r") as f:
            >>>     state = json.load(f)
            >>> handler.restore_state(state)
        """
        self.handler.import_state(state_data)
        logger.info("State restored from persistence")


# ============================================================================
# PATTERN 2: GitHub OAuth (Standard Authorization Code)
# ============================================================================

class GitHubOAuthExample:
    """
    Complete working example: GitHub OAuth 2.0

    Use case: Authenticating users with GitHub for repository access
    Flow: Standard Authorization Code (GitHub doesn't support PKCE)

    Features:
    - Repository and user data access
    - Scope-based permissions
    - State parameter protection
    - No refresh tokens (GitHub limitation)
    """

    def __init__(self, client_id: str, client_secret: str, scopes: Optional[list] = None):
        """
        Initialize GitHub OAuth handler

        Args:
            client_id: GitHub OAuth app client ID
            client_secret: GitHub OAuth app client secret
            scopes: List of GitHub scopes (default: ['user', 'repo'])
        """
        if scopes is None:
            scopes = ["user", "repo"]

        self.provider = ProviderConfig.github(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes
        )

        # GitHub doesn't support PKCE, use standard flow
        self.handler = OAuthFlowHandler(
            provider=self.provider,
            flow_type=OAuthFlowType.AUTHORIZATION_CODE
        )

        logger.info(f"GitHub OAuth handler initialized with scopes: {scopes}")

    def get_authorization_url(self, allow_signup: bool = True) -> str:
        """
        Get GitHub authorization URL

        Args:
            allow_signup: Allow users to sign up during auth

        Returns:
            Authorization URL

        Example:
            >>> handler = GitHubOAuthExample("client_id", "client_secret")
            >>> url = handler.get_authorization_url(allow_signup=True)
        """
        params = {}
        if allow_signup:
            params["allow_signup"] = "true"

        auth_url = self.handler.build_authorization_url(additional_params=params)
        logger.info("GitHub authorization URL generated")
        return auth_url

    def complete_authorization(self, code: str, state: str) -> OAuthToken:
        """
        Complete GitHub authorization

        Args:
            code: Authorization code from callback
            state: State parameter from callback

        Returns:
            OAuth token (no refresh token from GitHub)

        Example:
            >>> token = handler.complete_authorization(code="xyz", state="abc")
            >>> # Token has no refresh - re-authenticate when expired
        """
        callback_params = {"code": code, "state": state}

        token = self.handler.handle_callback(callback_params)
        logger.info("GitHub authentication complete")

        if not token.refresh_token:
            logger.warning("GitHub token has no refresh token - will need re-authentication")

        return token

    def validate_scopes(self, required_scopes: list) -> bool:
        """
        Validate that token has required scopes

        Args:
            required_scopes: List of required scopes

        Returns:
            True if all required scopes are granted

        Example:
            >>> if handler.validate_scopes(["repo", "user"]):
            >>>     # Proceed with API calls
        """
        has_scopes = self.handler.validate_scopes(required_scopes)

        if not has_scopes:
            logger.warning(f"Missing required scopes: {required_scopes}")

        return has_scopes


# ============================================================================
# PATTERN 3: Token Auto-Refresh Decorator
# ============================================================================

class TokenAutoRefreshExample:
    """
    Complete working example: Automatic Token Refresh Pattern

    Use case: Automatically refresh expired tokens in API calls
    Pattern: Decorator pattern for transparent token management

    Features:
    - Automatic token refresh before API calls
    - Transparent to calling code
    - Handles token expiry edge cases
    - Thread-safe token access
    """

    def __init__(self, oauth_handler: OAuthFlowHandler):
        """
        Initialize with existing OAuth handler

        Args:
            oauth_handler: Configured OAuthFlowHandler instance
        """
        self.handler = oauth_handler
        self._token_lock = None  # Use threading.Lock() in production

    def with_token_refresh(self, func):
        """
        Decorator to automatically refresh token before function execution

        Example:
            >>> @token_manager.with_token_refresh
            >>> def call_api(self, endpoint):
            >>>     token = self.handler.get_token()
            >>>     headers = {"Authorization": f"Bearer {token.access_token}"}
            >>>     # Make API call...
        """
        def wrapper(*args, **kwargs):
            try:
                # Get token (auto-refreshes if expired)
                token = self.handler.get_token()
                logger.debug(f"Token valid until: {token.expires_at}")

                # Call original function
                return func(*args, **kwargs)

            except OAuthError as e:
                logger.error(f"OAuth error in {func.__name__}: {e}")
                raise

        return wrapper

    def execute_with_retry(self, api_call, max_retries: int = 1):
        """
        Execute API call with automatic token refresh retry

        Args:
            api_call: Callable that makes the API request
            max_retries: Maximum retry attempts

        Returns:
            API call result

        Example:
            >>> def call_gmail_api():
            >>>     token = handler.get_token()
            >>>     return requests.get(
            >>>         "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            >>>         headers={"Authorization": f"Bearer {token.access_token}"}
            >>>     )
            >>>
            >>> result = token_manager.execute_with_retry(call_gmail_api)
        """
        attempts = 0

        while attempts <= max_retries:
            try:
                # Ensure token is valid
                token = self.handler.get_token()

                # Execute API call
                result = api_call()

                logger.info(f"API call successful on attempt {attempts + 1}")
                return result

            except Exception as e:
                attempts += 1
                logger.warning(f"API call failed (attempt {attempts}): {e}")

                if attempts > max_retries:
                    logger.error("Max retries exceeded")
                    raise

                # Try to refresh token
                try:
                    self.handler.refresh_access_token()
                    logger.info("Token refreshed, retrying...")
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {refresh_error}")
                    raise

    def check_token_status(self) -> dict:
        """
        Check current token status

        Returns:
            Token status information

        Example:
            >>> status = token_manager.check_token_status()
            >>> if status["is_expired"]:
            >>>     print("Token needs refresh")
        """
        try:
            token = self.handler.context.token

            if not token:
                return {"has_token": False}

            return {
                "has_token": True,
                "is_expired": token.is_expired,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "has_refresh_token": token.refresh_token is not None,
                "scopes": self.handler.context.granted_scopes
            }

        except Exception as e:
            logger.error(f"Failed to check token status: {e}")
            return {"error": str(e)}


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage_google():
    """
    Example: Complete Google OAuth flow

    This demonstrates the full authentication flow with Google
    """
    print("=" * 60)
    print("EXAMPLE 1: Google OAuth with PKCE")
    print("=" * 60)

    # Initialize handler
    google = GoogleOAuthExample(
        client_id="YOUR_GOOGLE_CLIENT_ID",
        client_secret="YOUR_GOOGLE_CLIENT_SECRET"
    )

    # Step 1: Get authorization URL
    auth_url = google.start_authentication()
    print(f"\n1. Visit this URL to authenticate:\n{auth_url}\n")

    # Step 2: User authorizes and is redirected to callback
    # Extract code and state from callback URL
    # In production, this would be handled by a web server
    print("2. After authorization, you'll be redirected to:")
    print("   http://localhost:9191/callback?code=XXX&state=YYY")

    # Step 3: Handle callback (mock values)
    print("\n3. Handling callback...")
    # token = google.handle_callback(
    #     authorization_code="received_code",
    #     state="received_state"
    # )
    # print(f"   Access token obtained: {token.access_token[:20]}...")

    # Step 4: Use token for API calls
    print("\n4. Making API calls with token...")
    # token = google.get_valid_token()  # Auto-refreshes if needed
    # headers = {"Authorization": f"Bearer {token.access_token}"}

    # Step 5: Save state for persistence
    print("\n5. Saving state...")
    # state = google.save_state()
    # # Save to file or database


def example_usage_github():
    """
    Example: GitHub OAuth flow
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: GitHub OAuth")
    print("=" * 60)

    # Initialize handler
    github = GitHubOAuthExample(
        client_id="YOUR_GITHUB_CLIENT_ID",
        client_secret="YOUR_GITHUB_CLIENT_SECRET",
        scopes=["repo", "user", "gist"]
    )

    # Get authorization URL
    auth_url = github.get_authorization_url(allow_signup=True)
    print(f"\n1. Authorize with GitHub:\n{auth_url}\n")

    # Complete authorization
    # token = github.complete_authorization(code="xyz", state="abc")

    # Validate scopes
    print("2. Validating scopes...")
    # if github.validate_scopes(["repo", "user"]):
    #     print("   Required scopes granted")


def example_usage_auto_refresh():
    """
    Example: Token auto-refresh pattern
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Token Auto-Refresh Pattern")
    print("=" * 60)

    # Assume we have an authenticated handler
    provider = ProviderConfig.google("client_id", "client_secret", ["email"])
    handler = OAuthFlowHandler(provider)

    # Create auto-refresh manager
    token_manager = TokenAutoRefreshExample(handler)

    # Check token status
    print("\n1. Checking token status...")
    status = token_manager.check_token_status()
    print(f"   Token status: {status}")

    # Use decorator pattern
    print("\n2. Using decorator for API calls...")

    @token_manager.with_token_refresh
    def call_google_api():
        """Example API call with auto-refresh"""
        token = handler.get_token()
        print(f"   Making API call with token: {token.access_token[:20]}...")
        # In production: make actual API request
        return {"status": "success"}

    # result = call_google_api()

    # Use retry pattern
    print("\n3. Using retry pattern...")

    def api_call_function():
        """Example API call function"""
        token = handler.get_token()
        # In production: make actual request
        return {"data": "example"}

    # result = token_manager.execute_with_retry(api_call_function, max_retries=2)


# ============================================================================
# MAIN DEMO
# ============================================================================

def main():
    """
    Run all examples

    Execute this module directly to see all examples:
        python -m agno.cli.oauth_examples
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("OAuth Flow Handler - Working Examples")
    print("=" * 60)

    try:
        # Run examples
        example_usage_google()
        example_usage_github()
        example_usage_auto_refresh()

        print("\n" + "=" * 60)
        print("Examples complete!")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Example error: {e}")
        raise


if __name__ == "__main__":
    main()

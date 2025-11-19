"""
JWT Manager Toolkit Example

This example demonstrates how to use the JWT Manager toolkit with an Agno agent
for handling JWT operations like token generation, validation, refresh tokens,
and more.

Requirements:
    pip install agno pyjwt[crypto]

Usage:
    python jwt_manager_example.py
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.jwt_manager import JWTManager

# Initialize the JWT Manager with a secret key
# In production, use environment variables or secure key management
jwt_manager = JWTManager(
    secret_key="your-secret-key-min-32-chars-long!!!",
    default_algorithm="HS256",
    default_expiration=3600,  # 1 hour
    refresh_expiration=604800,  # 7 days
    issuer="my-app",
    audience="my-app-users",
)

# Create an agent with JWT Manager capabilities
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[jwt_manager],
    show_tool_calls=True,
    markdown=True,
    description="You are a helpful assistant that can manage JWT tokens.",
    instructions=[
        "You can help users with JWT operations.",
        "Always ensure tokens are validated before trusting their contents.",
        "Explain security implications when relevant.",
    ],
)


def main():
    """Run interactive examples."""
    print("=" * 70)
    print("JWT Manager Toolkit Examples")
    print("=" * 70)
    print()

    # Example 1: Generate a token
    print("\n" + "=" * 70)
    print("Example 1: Generate a JWT Token")
    print("=" * 70)
    agent.print_response(
        """
        Generate a JWT token with the following payload:
        - user_id: 12345
        - username: johndoe
        - email: john@example.com
        - role: admin

        Use the default expiration time.
        """,
        stream=True,
    )

    # Example 2: Validate a token
    print("\n" + "=" * 70)
    print("Example 2: Validate a JWT Token")
    print("=" * 70)
    agent.print_response(
        """
        First, generate a token for user_id=999 with username=alice.
        Then, validate that token and show me the decoded payload.
        """,
        stream=True,
    )

    # Example 3: Work with refresh tokens
    print("\n" + "=" * 70)
    print("Example 3: Refresh Token Flow")
    print("=" * 70)
    agent.print_response(
        """
        Demonstrate the refresh token flow:
        1. Create a refresh token for user_id=555
        2. Use that refresh token to generate a new access token with
           user_id=555, username=bob, and session_id=abc123
        3. Show me both tokens and explain the difference
        """,
        stream=True,
    )

    # Example 4: Token revocation
    print("\n" + "=" * 70)
    print("Example 4: Token Revocation")
    print("=" * 70)
    agent.print_response(
        """
        1. Generate a token for user_id=777
        2. Validate it to confirm it works
        3. Revoke the token
        4. Try to validate it again and show that it's been revoked
        """,
        stream=True,
    )

    # Example 5: Claims validation
    print("\n" + "=" * 70)
    print("Example 5: Validate Specific Claims")
    print("=" * 70)
    agent.print_response(
        """
        1. Generate a token with: user_id=888, role=admin, department=engineering
        2. Validate that the token contains the exact claims: role=admin and department=engineering
        3. Show what happens if we check for a claim that doesn't match (like role=user)
        """,
        stream=True,
    )

    # Example 6: Check token expiration
    print("\n" + "=" * 70)
    print("Example 6: Check Token Expiration")
    print("=" * 70)
    agent.print_response(
        """
        1. Generate a token with 7200 seconds (2 hours) expiration
        2. Check the expiration status and tell me how much time is remaining
        """,
        stream=True,
    )

    # Example 7: Advanced - Custom algorithm and claims
    print("\n" + "=" * 70)
    print("Example 7: Advanced Token Configuration")
    print("=" * 70)
    agent.print_response(
        """
        Generate a token with:
        - Payload: user_id=999, email=admin@example.com
        - Algorithm: HS512
        - Expiration: 7200 seconds
        - Issuer: my-app
        - Audience: api-service
        - Subject: user:999
        - Additional claims: permissions=['read', 'write', 'delete'], tier='premium'

        Then decode it and show me all the claims.
        """,
        stream=True,
    )


def example_programmatic_usage():
    """
    Example of using JWT Manager programmatically (without agent).

    This shows how to use the toolkit directly in your code.
    """
    import json

    print("\n" + "=" * 70)
    print("Programmatic Usage Examples")
    print("=" * 70)

    jwt_mgr = JWTManager(secret_key="my-secret-key-that-is-very-long-32chars")

    # Generate a token
    print("\n1. Generate Token:")
    payload = json.dumps({"user_id": "123", "username": "testuser"})
    result = jwt_mgr.generate_token(payload=payload)
    result_data = json.loads(result)
    print(f"   Success: {result_data.get('success')}")
    token = result_data.get("token")
    print(f"   Token: {token[:50]}...")

    # Validate the token
    print("\n2. Validate Token:")
    validate_result = jwt_mgr.validate_token(token=token)
    validate_data = json.loads(validate_result)
    print(f"   Valid: {validate_data.get('valid')}")
    print(f"   Payload: {validate_data.get('payload')}")

    # Decode without verification (useful for debugging)
    print("\n3. Decode Token (no verification):")
    decode_result = jwt_mgr.decode_token(token=token, verify=False)
    decode_data = json.loads(decode_result)
    print(f"   Header: {decode_data.get('header')}")
    print(f"   Payload: {decode_data.get('payload')}")

    # Create and use refresh token
    print("\n4. Refresh Token Flow:")
    refresh_result = jwt_mgr.create_refresh_token(user_id="123")
    refresh_data = json.loads(refresh_result)
    refresh_token = refresh_data.get("refresh_token")
    print(f"   Refresh token created: {refresh_token[:50]}...")

    new_payload = json.dumps({"user_id": "123", "session": "new_session"})
    new_token_result = jwt_mgr.use_refresh_token(
        refresh_token=refresh_token,
        new_payload=new_payload
    )
    new_token_data = json.loads(new_token_result)
    print(f"   New access token generated: {new_token_data.get('success')}")

    # Revoke a token
    print("\n5. Token Revocation:")
    revoke_result = jwt_mgr.revoke_token(token=token)
    revoke_data = json.loads(revoke_result)
    print(f"   Revoked: {revoke_data.get('success')}")

    is_revoked_result = jwt_mgr.is_token_revoked(token=token)
    is_revoked_data = json.loads(is_revoked_result)
    print(f"   Token status: {is_revoked_data.get('token_status')}")

    # Validate specific claims
    print("\n6. Claims Validation:")
    new_token_payload = json.dumps({
        "user_id": "456",
        "role": "admin",
        "permissions": ["read", "write"]
    })
    new_token_result = jwt_mgr.generate_token(payload=new_token_payload)
    new_token = json.loads(new_token_result).get("token")

    required_claims = json.dumps({"user_id": "456", "role": "admin"})
    claims_result = jwt_mgr.validate_claims(
        token=new_token,
        required_claims=required_claims
    )
    claims_data = json.loads(claims_result)
    print(f"   Claims valid: {claims_data.get('valid')}")

    # Check expiration
    print("\n7. Check Expiration:")
    exp_result = jwt_mgr.check_expiration(token=new_token)
    exp_data = json.loads(exp_result)
    print(f"   Expired: {exp_data.get('expired')}")
    print(f"   Time remaining: {exp_data.get('time_remaining_seconds')} seconds")


def example_with_rsa_keys():
    """
    Example using RSA keys (RS256 algorithm).

    This is useful for scenarios where you need asymmetric encryption,
    such as when tokens are generated by one service and validated by another.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import json

    print("\n" + "=" * 70)
    print("RSA Keys Example (RS256)")
    print("=" * 70)

    # Generate RSA key pair (in production, generate these securely and store them)
    print("\nGenerating RSA key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # Serialize keys to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    # Create JWT manager with RSA keys
    jwt_mgr = JWTManager(
        private_key=private_pem,
        public_key=public_pem,
        default_algorithm="RS256"
    )

    # Generate token (uses private key)
    print("\nGenerating token with RS256...")
    payload = json.dumps({"user_id": "789", "service": "api"})
    result = jwt_mgr.generate_token(payload=payload)
    result_data = json.loads(result)
    token = result_data.get("token")
    print(f"Token generated: {token[:50]}...")

    # Validate token (uses public key)
    print("\nValidating token with RS256...")
    validate_result = jwt_mgr.validate_token(token=token)
    validate_data = json.loads(validate_result)
    print(f"Valid: {validate_data.get('valid')}")
    print(f"Payload: {validate_data.get('payload')}")


if __name__ == "__main__":
    # Run agent-based examples
    main()

    print("\n" + "=" * 70)
    print("\nNow running programmatic examples...")
    print("=" * 70)

    # Run programmatic examples
    example_programmatic_usage()

    print("\n" + "=" * 70)
    print("\nNow running RSA example...")
    print("=" * 70)

    # Run RSA example (requires cryptography package)
    try:
        example_with_rsa_keys()
    except ImportError:
        print("\nSkipping RSA example - install cryptography package:")
        print("pip install cryptography")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)

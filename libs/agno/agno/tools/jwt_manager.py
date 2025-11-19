"""JWT Manager Toolkit for Agno Framework.

A production-ready toolkit for handling JSON Web Token operations including:
- Token generation with configurable algorithms (HS256, RS256, ES256)
- Token validation and verification
- Payload encoding/decoding
- Expiration management
- Refresh token handling
- Token revocation/blacklisting
- Claims validation
- Audience and issuer verification
- Secure key management
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from os import getenv

from agno.tools import Toolkit
from agno.utils.log import logger

try:
    import jwt
    from jwt import PyJWTError
except ImportError:
    raise ImportError(
        "The `pyjwt` package is not installed. "
        "Please install it with `pip install pyjwt cryptography`"
    )


class JWTManager(Toolkit):
    """JWT Manager Toolkit for comprehensive JWT operations.

    This toolkit provides production-ready JWT functionality including token generation,
    validation, refresh tokens, blacklisting, and secure key management.

    Args:
        secret_key: Secret key for HS256/HS384/HS512 algorithms
        private_key: Private key for RS256/RS384/RS512 or ES256/ES384/ES512 algorithms
        public_key: Public key for RS256/RS384/RS512 or ES256/ES384/ES512 algorithms
        default_algorithm: Default algorithm for token generation (default: HS256)
        default_expiration: Default token expiration in seconds (default: 3600)
        refresh_expiration: Refresh token expiration in seconds (default: 604800 = 7 days)
        issuer: Default issuer claim
        audience: Default audience claim
        enable_generate_token: Enable token generation function
        enable_validate_token: Enable token validation function
        enable_decode_token: Enable token decoding function
        enable_refresh_token: Enable refresh token operations
        enable_revoke_token: Enable token revocation
        enable_validate_claims: Enable claims validation
        enable_check_expiration: Enable expiration checking
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        default_algorithm: str = "HS256",
        default_expiration: int = 3600,
        refresh_expiration: int = 604800,
        issuer: Optional[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
        enable_generate_token: bool = True,
        enable_validate_token: bool = True,
        enable_decode_token: bool = True,
        enable_refresh_token: bool = True,
        enable_revoke_token: bool = True,
        enable_validate_claims: bool = True,
        enable_check_expiration: bool = True,
    ):
        super().__init__(name="jwt_manager")

        # Load keys from environment if not provided
        self.secret_key = secret_key or getenv("JWT_SECRET_KEY")
        self.private_key = private_key or getenv("JWT_PRIVATE_KEY")
        self.public_key = public_key or getenv("JWT_PUBLIC_KEY")
        self.default_algorithm = default_algorithm
        self.default_expiration = default_expiration
        self.refresh_expiration = refresh_expiration
        self.issuer = issuer or getenv("JWT_ISSUER")
        self.audience = audience or getenv("JWT_AUDIENCE")

        # Token blacklist for revoked tokens
        self._blacklist: Set[str] = set()

        # Refresh token storage (in production, use a database)
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}

        # Register functions based on flags
        if enable_generate_token:
            self.register(self.generate_token)
        if enable_validate_token:
            self.register(self.validate_token)
        if enable_decode_token:
            self.register(self.decode_token)
        if enable_refresh_token:
            self.register(self.create_refresh_token)
            self.register(self.use_refresh_token)
        if enable_revoke_token:
            self.register(self.revoke_token)
            self.register(self.is_token_revoked)
        if enable_validate_claims:
            self.register(self.validate_claims)
        if enable_check_expiration:
            self.register(self.check_expiration)

    def _get_key_for_algorithm(self, algorithm: str, operation: str = "encode") -> Optional[str]:
        """Get appropriate key for the given algorithm and operation.

        Args:
            algorithm: JWT algorithm (HS256, RS256, ES256, etc.)
            operation: 'encode' or 'decode'

        Returns:
            The appropriate key or None
        """
        if algorithm.startswith("HS"):
            return self.secret_key
        elif algorithm.startswith("RS") or algorithm.startswith("ES"):
            if operation == "encode":
                return self.private_key
            else:
                return self.public_key
        return None

    def generate_token(
        self,
        payload: str,
        expiration: Optional[int] = None,
        algorithm: Optional[str] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        subject: Optional[str] = None,
        additional_claims: Optional[str] = None,
    ) -> str:
        """Generate a JWT token with the specified payload and claims.

        Args:
            payload: JSON string of the main payload data
            expiration: Token expiration in seconds (overrides default)
            algorithm: JWT algorithm to use (HS256, RS256, ES256, etc.)
            issuer: Token issuer claim
            audience: Token audience claim
            subject: Token subject claim
            additional_claims: JSON string of additional claims to include

        Returns:
            JSON string containing the generated token or error
        """
        try:
            # Parse payload
            payload_data = json.loads(payload)

            # Set algorithm
            algo = algorithm or self.default_algorithm

            # Get appropriate key
            key = self._get_key_for_algorithm(algo, "encode")
            if not key:
                return json.dumps({
                    "error": f"No key configured for algorithm {algo}"
                })

            # Build claims
            claims = payload_data.copy()

            # Add standard claims
            exp_seconds = expiration or self.default_expiration
            claims["exp"] = datetime.utcnow() + timedelta(seconds=exp_seconds)
            claims["iat"] = datetime.utcnow()
            claims["nbf"] = datetime.utcnow()

            if issuer or self.issuer:
                claims["iss"] = issuer or self.issuer
            if audience or self.audience:
                claims["aud"] = audience or self.audience
            if subject:
                claims["sub"] = subject

            # Add additional claims
            if additional_claims:
                extra = json.loads(additional_claims)
                claims.update(extra)

            # Generate token
            token = jwt.encode(claims, key, algorithm=algo)

            logger.debug(f"Generated JWT token with algorithm {algo}")

            return json.dumps({
                "success": True,
                "token": token,
                "algorithm": algo,
                "expires_in": exp_seconds,
                "expires_at": claims["exp"].isoformat(),
            })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in payload: {e}")
            return json.dumps({"error": f"Invalid JSON: {str(e)}"})
        except PyJWTError as e:
            logger.error(f"JWT encoding error: {e}")
            return json.dumps({"error": f"JWT encoding error: {str(e)}"})
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            return json.dumps({"error": str(e)})

    def validate_token(
        self,
        token: str,
        algorithm: Optional[str] = None,
        verify_expiration: bool = True,
        verify_audience: bool = True,
        verify_issuer: bool = True,
        audience: Optional[str] = None,
        issuer: Optional[str] = None,
    ) -> str:
        """Validate a JWT token and return its payload if valid.

        Args:
            token: The JWT token to validate
            algorithm: Expected algorithm (defaults to default_algorithm)
            verify_expiration: Whether to verify token expiration
            verify_audience: Whether to verify audience claim
            verify_issuer: Whether to verify issuer claim
            audience: Expected audience (uses default if not provided)
            issuer: Expected issuer (uses default if not provided)

        Returns:
            JSON string containing validation result and payload or error
        """
        try:
            # Check if token is revoked
            if token in self._blacklist:
                return json.dumps({
                    "valid": False,
                    "error": "Token has been revoked"
                })

            # Set algorithm
            algo = algorithm or self.default_algorithm
            algorithms = [algo] if algo else None

            # Get appropriate key
            key = self._get_key_for_algorithm(algo, "decode")
            if not key:
                return json.dumps({
                    "valid": False,
                    "error": f"No key configured for algorithm {algo}"
                })

            # Build verification options
            options = {
                "verify_exp": verify_expiration,
                "verify_aud": verify_audience,
                "verify_iss": verify_issuer,
            }

            # Decode and validate
            payload = jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience=audience or self.audience if verify_audience else None,
                issuer=issuer or self.issuer if verify_issuer else None,
                options=options,
            )

            logger.debug("Token validated successfully")

            return json.dumps({
                "valid": True,
                "payload": payload,
                "algorithm": algo,
            })

        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: expired")
            return json.dumps({
                "valid": False,
                "error": "Token has expired"
            })
        except jwt.InvalidAudienceError:
            logger.warning("Token validation failed: invalid audience")
            return json.dumps({
                "valid": False,
                "error": "Invalid audience"
            })
        except jwt.InvalidIssuerError:
            logger.warning("Token validation failed: invalid issuer")
            return json.dumps({
                "valid": False,
                "error": "Invalid issuer"
            })
        except PyJWTError as e:
            logger.error(f"JWT validation error: {e}")
            return json.dumps({
                "valid": False,
                "error": f"JWT validation error: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return json.dumps({
                "valid": False,
                "error": str(e)
            })

    def decode_token(self, token: str, verify: bool = False) -> str:
        """Decode a JWT token without verification (useful for debugging).

        Args:
            token: The JWT token to decode
            verify: Whether to verify the signature (default: False)

        Returns:
            JSON string containing the decoded payload and header or error
        """
        try:
            if verify:
                # Use validate_token for verified decoding
                result = self.validate_token(token)
                return result

            # Decode without verification
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={"verify_signature": False})

            logger.debug("Token decoded successfully")

            return json.dumps({
                "success": True,
                "header": header,
                "payload": payload,
            })

        except PyJWTError as e:
            logger.error(f"JWT decoding error: {e}")
            return json.dumps({"error": f"JWT decoding error: {str(e)}"})
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return json.dumps({"error": str(e)})

    def create_refresh_token(
        self,
        user_id: str,
        payload: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Create a refresh token for the given user.

        Args:
            user_id: Unique identifier for the user
            payload: Optional JSON string of additional payload data
            algorithm: JWT algorithm to use (defaults to default_algorithm)

        Returns:
            JSON string containing the refresh token or error
        """
        try:
            # Parse payload if provided
            payload_data = json.loads(payload) if payload else {}

            # Set algorithm
            algo = algorithm or self.default_algorithm

            # Get appropriate key
            key = self._get_key_for_algorithm(algo, "encode")
            if not key:
                return json.dumps({
                    "error": f"No key configured for algorithm {algo}"
                })

            # Build claims
            claims = {
                "user_id": user_id,
                "type": "refresh",
                "exp": datetime.utcnow() + timedelta(seconds=self.refresh_expiration),
                "iat": datetime.utcnow(),
            }
            claims.update(payload_data)

            # Generate token
            refresh_token = jwt.encode(claims, key, algorithm=algo)

            # Store refresh token metadata
            self._refresh_tokens[refresh_token] = {
                "user_id": user_id,
                "created_at": time.time(),
                "used": False,
            }

            logger.debug(f"Created refresh token for user {user_id}")

            return json.dumps({
                "success": True,
                "refresh_token": refresh_token,
                "expires_in": self.refresh_expiration,
            })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in payload: {e}")
            return json.dumps({"error": f"Invalid JSON: {str(e)}"})
        except PyJWTError as e:
            logger.error(f"JWT encoding error: {e}")
            return json.dumps({"error": f"JWT encoding error: {str(e)}"})
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            return json.dumps({"error": str(e)})

    def use_refresh_token(
        self,
        refresh_token: str,
        new_payload: str,
        algorithm: Optional[str] = None,
    ) -> str:
        """Use a refresh token to generate a new access token.

        Args:
            refresh_token: The refresh token
            new_payload: JSON string of payload for the new access token
            algorithm: JWT algorithm to use (defaults to default_algorithm)

        Returns:
            JSON string containing the new access token or error
        """
        try:
            # Check if refresh token exists
            if refresh_token not in self._refresh_tokens:
                return json.dumps({
                    "error": "Invalid refresh token"
                })

            # Check if already used (one-time use)
            if self._refresh_tokens[refresh_token]["used"]:
                return json.dumps({
                    "error": "Refresh token already used"
                })

            # Validate refresh token
            validation_result = json.loads(self.validate_token(refresh_token, algorithm=algorithm))

            if not validation_result.get("valid"):
                return json.dumps({
                    "error": validation_result.get("error", "Invalid refresh token")
                })

            # Mark as used
            self._refresh_tokens[refresh_token]["used"] = True

            # Generate new access token
            result = self.generate_token(
                payload=new_payload,
                algorithm=algorithm,
            )

            logger.debug("Generated new access token from refresh token")

            return result

        except Exception as e:
            logger.error(f"Error using refresh token: {e}")
            return json.dumps({"error": str(e)})

    def revoke_token(self, token: str) -> str:
        """Revoke a token by adding it to the blacklist.

        Args:
            token: The token to revoke

        Returns:
            JSON string confirming revocation
        """
        try:
            self._blacklist.add(token)
            logger.info(f"Token revoked and added to blacklist")

            return json.dumps({
                "success": True,
                "message": "Token revoked successfully"
            })

        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return json.dumps({"error": str(e)})

    def is_token_revoked(self, token: str) -> str:
        """Check if a token has been revoked.

        Args:
            token: The token to check

        Returns:
            JSON string indicating if token is revoked
        """
        try:
            revoked = token in self._blacklist

            return json.dumps({
                "revoked": revoked,
                "token_status": "revoked" if revoked else "active"
            })

        except Exception as e:
            logger.error(f"Error checking token revocation: {e}")
            return json.dumps({"error": str(e)})

    def validate_claims(
        self,
        token: str,
        required_claims: str,
        algorithm: Optional[str] = None,
    ) -> str:
        """Validate that a token contains specific claims with expected values.

        Args:
            token: The JWT token to validate
            required_claims: JSON string of required claims and their expected values
            algorithm: Expected algorithm (defaults to default_algorithm)

        Returns:
            JSON string indicating if all claims are valid
        """
        try:
            # Parse required claims
            required = json.loads(required_claims)

            # Decode token
            decode_result = json.loads(self.validate_token(token, algorithm=algorithm))

            if not decode_result.get("valid"):
                return json.dumps({
                    "valid": False,
                    "error": decode_result.get("error", "Invalid token")
                })

            payload = decode_result.get("payload", {})

            # Validate each required claim
            missing_claims = []
            invalid_claims = []

            for claim, expected_value in required.items():
                if claim not in payload:
                    missing_claims.append(claim)
                elif payload[claim] != expected_value:
                    invalid_claims.append({
                        "claim": claim,
                        "expected": expected_value,
                        "actual": payload[claim]
                    })

            if missing_claims or invalid_claims:
                return json.dumps({
                    "valid": False,
                    "missing_claims": missing_claims,
                    "invalid_claims": invalid_claims,
                })

            logger.debug("All required claims validated successfully")

            return json.dumps({
                "valid": True,
                "message": "All required claims are valid"
            })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in required_claims: {e}")
            return json.dumps({"error": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            logger.error(f"Error validating claims: {e}")
            return json.dumps({"error": str(e)})

    def check_expiration(self, token: str) -> str:
        """Check the expiration status of a token.

        Args:
            token: The JWT token to check

        Returns:
            JSON string with expiration information
        """
        try:
            # Decode without verification to get expiration
            payload = jwt.decode(token, options={"verify_signature": False})

            if "exp" not in payload:
                return json.dumps({
                    "error": "Token does not contain expiration claim"
                })

            exp_timestamp = payload["exp"]
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            now = datetime.utcnow()

            is_expired = now > exp_datetime
            time_remaining = (exp_datetime - now).total_seconds() if not is_expired else 0

            logger.debug(f"Token expiration check: expired={is_expired}")

            return json.dumps({
                "expired": is_expired,
                "expiration_time": exp_datetime.isoformat(),
                "current_time": now.isoformat(),
                "time_remaining_seconds": max(0, time_remaining),
                "status": "expired" if is_expired else "valid"
            })

        except PyJWTError as e:
            logger.error(f"JWT decoding error: {e}")
            return json.dumps({"error": f"JWT decoding error: {str(e)}"})
        except Exception as e:
            logger.error(f"Error checking expiration: {e}")
            return json.dumps({"error": str(e)})

    def instructions(self) -> str:
        """Return instructions for using the JWT Manager toolkit."""
        return """JWT Manager Toolkit - Comprehensive JWT Operations

This toolkit provides production-ready JWT (JSON Web Token) functionality:

**Token Generation:**
- Use `generate_token` to create new JWT tokens with custom payloads
- Supports HS256, RS256, ES256 and other standard algorithms
- Configure expiration, issuer, audience, and custom claims

**Token Validation:**
- Use `validate_token` to verify token signatures and claims
- Validates expiration, audience, issuer, and other standard claims
- Returns decoded payload if valid

**Token Decoding:**
- Use `decode_token` to inspect token contents without verification
- Useful for debugging and analyzing token structure

**Refresh Tokens:**
- Use `create_refresh_token` to generate long-lived refresh tokens
- Use `use_refresh_token` to exchange refresh tokens for new access tokens
- Implements one-time use pattern for security

**Token Revocation:**
- Use `revoke_token` to blacklist tokens
- Use `is_token_revoked` to check revocation status

**Claims Validation:**
- Use `validate_claims` to verify specific claim values
- Use `check_expiration` to inspect token expiration status

**Security Notes:**
- All functions return JSON strings
- Tokens are validated against configured keys
- Revoked tokens are tracked in an in-memory blacklist
- For production use, persist blacklist and refresh tokens to a database
"""

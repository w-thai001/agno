# OAuth Pattern Library and Best Practices

**Version**: 1.0
**Framework**: Agno OAuth FSA Handler
**Last Updated**: 2025-11-19

---

## Table of Contents

1. [Overview](#overview)
2. [Pattern Library](#pattern-library)
3. [Anti-Patterns](#anti-patterns)
4. [Usage Recommendations](#usage-recommendations)
5. [Refactoring Suggestions](#refactoring-suggestions)
6. [Security Best Practices](#security-best-practices)
7. [Quick Reference](#quick-reference)

---

## Overview

This document provides a comprehensive pattern library for OAuth 2.0 implementations in the Agno framework. It includes:

- **Proven patterns** for common OAuth scenarios
- **Anti-patterns** to avoid
- **Usage recommendations** for different use cases
- **Refactoring suggestions** for existing code
- **Security best practices** for production deployments

### Key Components

- **OAuthFlowHandler**: Finite State Automaton for OAuth flows
- **OAuthPatternAnalyzer**: Automated pattern discovery and analysis
- **Provider Configurations**: Pre-built configs for Google, GitHub, Microsoft

---

## Pattern Library

### 1. PKCE Challenge Generation (Security)

**Pattern ID**: `pkce_gen_001`
**Category**: Security Practice
**Complexity**: Medium

#### Description
Generate cryptographically secure PKCE code verifier and challenge using SHA256.

#### Implementation

```python
def generate_pkce_challenge(self) -> tuple[str, str]:
    """Generate PKCE code verifier and challenge"""
    import secrets
    import hashlib
    import base64

    # Generate random verifier (43-128 characters)
    self.code_verifier = secrets.token_urlsafe(96)[:128]

    # Create SHA256 challenge
    challenge = hashlib.sha256(self.code_verifier.encode()).digest()
    self.code_challenge = base64.urlsafe_b64encode(challenge).decode().rstrip('=')

    return self.code_verifier, self.code_challenge
```

#### When to Use
- ✅ Authorization Code flow with public clients
- ✅ Mobile applications
- ✅ Single-page applications (SPAs)
- ✅ Desktop applications

#### Benefits
- Prevents authorization code interception attacks
- No client secret required
- Enhanced security for public clients

#### Related Patterns
- State Parameter Validation
- Token Exchange with PKCE

---

### 2. Timing-Safe State Validation (Security)

**Pattern ID**: `state_val_001`
**Category**: Security Practice
**Complexity**: Low

#### Description
Use constant-time comparison for state parameter validation to prevent timing attacks.

#### Implementation

```python
def validate_state(self, received_state: str) -> bool:
    """Validate state parameter using timing-safe comparison"""
    import secrets

    if not self.state_parameter:
        return False

    # Use secrets.compare_digest for timing-safe comparison
    return secrets.compare_digest(self.state_parameter, received_state)
```

#### Why Timing-Safe?
Regular string comparison (`==`) can leak information through timing differences. Attackers can use timing analysis to guess the state parameter.

#### Anti-Pattern (AVOID)

```python
# ❌ DON'T DO THIS
def validate_state(self, received_state: str) -> bool:
    return received_state == self.state_parameter  # Timing attack vulnerable!
```

#### When to Use
- ✅ Always for state parameter validation
- ✅ Any security-critical string comparison
- ✅ Token comparison
- ✅ CSRF token validation

---

### 3. Token Expiry with Buffer (Token Management)

**Pattern ID**: `token_exp_001`
**Category**: Token Management
**Complexity**: Low

#### Description
Check token expiry with a buffer time (typically 60 seconds) to account for clock skew and network latency.

#### Implementation

```python
@property
def is_expired(self) -> bool:
    """Check if token is expired with 60-second buffer"""
    if not self.expires_in:
        return False

    # Add 60-second buffer for clock skew
    buffer_seconds = 60
    expiry_time = self.issued_at + self.expires_in - buffer_seconds

    return time.time() >= expiry_time
```

#### Why Use a Buffer?

1. **Clock Skew**: Client and server clocks may not be perfectly synchronized
2. **Network Latency**: API calls take time to complete
3. **Safety Margin**: Prevents using tokens that expire during request

#### Buffer Recommendations

| Use Case | Recommended Buffer |
|----------|-------------------|
| Production API calls | 60 seconds |
| Background jobs | 120 seconds |
| Batch operations | 300 seconds |
| Quick requests | 30 seconds |

---

### 4. Automatic Token Refresh (Token Management)

**Pattern ID**: `token_ref_001`
**Category**: Token Management
**Complexity**: Medium

#### Description
Automatically refresh expired access tokens when accessed, transparent to calling code.

#### Implementation

```python
def get_token(self) -> OAuthToken:
    """Get valid token, auto-refreshing if expired"""
    if self.context.state != OAuthState.AUTHENTICATED:
        raise OAuthError("Not authenticated")

    if not self.context.token:
        raise OAuthError("No token available")

    # Auto-refresh if expired
    if self.context.token.is_expired:
        if self.context.provider.supports_refresh and self.context.token.refresh_token:
            return self.refresh_access_token()
        else:
            raise TokenExpiredError("Token expired and cannot be refreshed")

    return self.context.token
```

#### Usage Pattern

```python
# Application code - no manual refresh needed!
def call_api(self):
    # Automatically refreshes if needed
    token = self.oauth_handler.get_token()

    headers = {"Authorization": f"Bearer {token.access_token}"}
    response = requests.get("https://api.example.com/data", headers=headers)
    return response.json()
```

#### Benefits
- Transparent to application code
- Reduces token-related errors
- Better user experience (no re-authentication)

---

### 5. State Machine Transition Validation (FSA)

**Pattern ID**: `fsm_val_001`
**Category**: State Transition
**Complexity**: High

#### Description
Validate all state transitions before execution to maintain FSA integrity.

#### Implementation

```python
def _is_valid_transition(self, from_state: OAuthState, to_state: OAuthState) -> bool:
    """Validate state transition"""
    valid_transitions = {
        OAuthState.INITIAL: {
            OAuthState.AUTHORIZATION_REQUESTED,
            OAuthState.ERROR
        },
        OAuthState.AUTHORIZATION_REQUESTED: {
            OAuthState.WAITING_FOR_CALLBACK,
            OAuthState.ERROR
        },
        OAuthState.WAITING_FOR_CALLBACK: {
            OAuthState.EXCHANGING_CODE,
            OAuthState.ERROR
        },
        OAuthState.EXCHANGING_CODE: {
            OAuthState.AUTHENTICATED,
            OAuthState.ERROR
        },
        OAuthState.AUTHENTICATED: {
            OAuthState.REFRESHING_TOKEN,
            OAuthState.EXPIRED,
            OAuthState.ERROR
        },
        OAuthState.REFRESHING_TOKEN: {
            OAuthState.AUTHENTICATED,
            OAuthState.ERROR
        },
        OAuthState.EXPIRED: {
            OAuthState.REFRESHING_TOKEN,
            OAuthState.INITIAL,
            OAuthState.ERROR
        },
        OAuthState.ERROR: {
            OAuthState.INITIAL
        }
    }

    return to_state in valid_transitions.get(from_state, set())

def _transition_to(self, new_state: OAuthState, **context_updates):
    """Transition with validation"""
    old_state = self.context.state

    # Validate transition
    if not self._is_valid_transition(old_state, new_state):
        raise OAuthError(f"Invalid transition: {old_state.name} -> {new_state.name}")

    # Execute transition
    for key, value in context_updates.items():
        setattr(self.context, key, value)

    self.context.state = new_state
```

#### State Diagram

```
INITIAL
  ↓
AUTHORIZATION_REQUESTED
  ↓
WAITING_FOR_CALLBACK
  ↓
EXCHANGING_CODE
  ↓
AUTHENTICATED ←→ REFRESHING_TOKEN
  ↓
EXPIRED
  ↓ (can refresh)
AUTHENTICATED

(Any state) → ERROR → INITIAL
```

---

### 6. Transition Hooks (FSA)

**Pattern ID**: `fsm_hook_001`
**Category**: State Transition
**Complexity**: Medium

#### Description
Register callbacks to execute on specific state transitions for logging, analytics, or side effects.

#### Implementation

```python
def register_transition_hook(
    self,
    from_state: OAuthState,
    to_state: OAuthState,
    hook: Callable
):
    """Register hook for state transition"""
    key = (from_state, to_state)
    if key not in self._transition_hooks:
        self._transition_hooks[key] = []
    self._transition_hooks[key].append(hook)

# Example usage
def log_authentication(context):
    logger.info(f"User authenticated with scopes: {context.granted_scopes}")

handler.register_transition_hook(
    OAuthState.EXCHANGING_CODE,
    OAuthState.AUTHENTICATED,
    log_authentication
)
```

#### Use Cases
- Analytics tracking
- Audit logging
- Cache invalidation
- Webhook notifications
- State persistence

---

### 7. Scope Validation (Validation)

**Pattern ID**: `scope_val_001`
**Category**: Validation
**Complexity**: Low

#### Description
Validate that granted scopes include all required scopes before API operations.

#### Implementation

```python
def validate_scopes(self, required_scopes: List[str]) -> bool:
    """Validate granted scopes contain required scopes"""
    return all(scope in self.context.granted_scopes for scope in required_scopes)

# Usage
if not handler.validate_scopes(["email", "profile"]):
    raise InsufficientScopesError("Missing required scopes")
```

---

### 8. State Export/Import (Persistence)

**Pattern ID**: `state_persist_001`
**Category**: State Management
**Complexity**: Medium

#### Description
Export and import OAuth state for persistence across sessions.

#### Implementation

```python
def export_state(self) -> Dict[str, Any]:
    """Export state for persistence"""
    return {
        "state": self.context.state.name,
        "flow_type": self.context.flow_type.name,
        "provider_name": self.context.provider.name,
        "token": self.context.token.to_dict() if self.context.token else None,
        "granted_scopes": self.context.granted_scopes,
        "state_parameter": self.context.state_parameter,
        "nonce": self.context.nonce
    }

def import_state(self, state_data: Dict[str, Any]):
    """Import state from persistence"""
    if state_data.get("token"):
        self.context.token = OAuthToken.from_dict(state_data["token"])
    self.context.granted_scopes = state_data.get("granted_scopes", [])
    self.context.state = OAuthState[state_data.get("state", "INITIAL")]
```

#### Storage Recommendations

```python
# File-based storage
import json

# Save
state = handler.export_state()
with open("oauth_state.json", "w") as f:
    json.dump(state, f)

# Load
with open("oauth_state.json", "r") as f:
    state = json.load(f)
handler.import_state(state)
```

---

## Anti-Patterns

### ❌ 1. Plain State Comparison

**Anti-Pattern ID**: `anti_001`
**Severity**: ERROR

```python
# ❌ DON'T DO THIS
def validate_state(self, received_state: str) -> bool:
    return received_state == self.state_parameter  # Timing attack!
```

**Why It's Bad**: Vulnerable to timing attacks

**Fix**:
```python
# ✅ DO THIS
import secrets
return secrets.compare_digest(self.state_parameter, received_state)
```

---

### ❌ 2. Missing PKCE for Public Clients

**Anti-Pattern ID**: `anti_002`
**Severity**: CRITICAL

```python
# ❌ DON'T DO THIS
# Using authorization code flow without PKCE in SPA
handler = OAuthFlowHandler(provider, OAuthFlowType.AUTHORIZATION_CODE)
```

**Why It's Bad**: Vulnerable to authorization code interception

**Fix**:
```python
# ✅ DO THIS
handler = OAuthFlowHandler(provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)
```

---

### ❌ 3. Hardcoded Client Secrets

**Anti-Pattern ID**: `anti_003`
**Severity**: CRITICAL

```python
# ❌ DON'T DO THIS
provider = ProviderConfig.google(
    client_id="my_client_id",
    client_secret="hardcoded_secret_123456",  # NEVER!
    scopes=["email"]
)
```

**Why It's Bad**: Secrets exposed in source code, version control

**Fix**:
```python
# ✅ DO THIS
import os

provider = ProviderConfig.google(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=["email"]
)
```

---

### ❌ 4. Missing State Parameter

**Anti-Pattern ID**: `anti_004`
**Severity**: CRITICAL

```python
# ❌ DON'T DO THIS
url = f"{auth_endpoint}?client_id={client_id}&redirect_uri={redirect_uri}"
# Missing state parameter!
```

**Why It's Bad**: Vulnerable to CSRF attacks

**Fix**:
```python
# ✅ DO THIS
# OAuthFlowHandler automatically includes state parameter
auth_url = handler.build_authorization_url()
```

---

### ❌ 5. Insecure Random Generation

**Anti-Pattern ID**: `anti_005`
**Severity**: CRITICAL

```python
# ❌ DON'T DO THIS
import random
state = str(random.random())  # Predictable!
```

**Why It's Bad**: Predictable values can be guessed by attackers

**Fix**:
```python
# ✅ DO THIS
import secrets
state = secrets.token_urlsafe(32)  # Cryptographically secure
```

---

### ❌ 6. No Token Expiry Check

**Anti-Pattern ID**: `anti_006`
**Severity**: WARNING

```python
# ❌ DON'T DO THIS
def get_access_token(self):
    return self.access_token  # May be expired!
```

**Why It's Bad**: API calls fail with expired tokens

**Fix**:
```python
# ✅ DO THIS
def get_access_token(self):
    if self.token.is_expired:
        self.refresh_access_token()
    return self.token.access_token
```

---

## Usage Recommendations

### Choosing the Right Flow

| Use Case | Recommended Flow | Why |
|----------|-----------------|-----|
| Web app (server-side) | Authorization Code | Secure, supports refresh |
| SPA (JavaScript) | Authorization Code + PKCE | No client secret needed |
| Mobile app | Authorization Code + PKCE | Enhanced security |
| Desktop app | Authorization Code + PKCE | Public client security |
| Machine-to-machine | Client Credentials | No user interaction |
| Legacy systems | Implicit Flow | ⚠️ Deprecated, use PKCE instead |

### Provider Selection Guide

#### Google OAuth
- **Best for**: Gmail, Calendar, Drive, YouTube APIs
- **Supports**: PKCE ✅, Refresh tokens ✅
- **Scopes**: Fine-grained (per API)

```python
provider = ProviderConfig.google(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.readonly"
    ]
)
```

#### GitHub OAuth
- **Best for**: Repository access, user info
- **Supports**: PKCE ❌, Refresh tokens ❌
- **Scopes**: Coarse-grained

```python
provider = ProviderConfig.github(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    scopes=["repo", "user"]
)
```

#### Microsoft OAuth
- **Best for**: Office 365, Azure AD
- **Supports**: PKCE ✅, Refresh tokens ✅
- **Scopes**: Microsoft Graph API

```python
provider = ProviderConfig.microsoft(
    client_id=os.environ["MICROSOFT_CLIENT_ID"],
    client_secret=os.environ["MICROSOFT_CLIENT_SECRET"],
    scopes=["User.Read", "Mail.Read"],
    tenant="common"  # or specific tenant ID
)
```

---

## Refactoring Suggestions

### 1. Migrate from Manual OAuth to FSA Handler

**Before**:
```python
class MyOAuthHandler:
    def __init__(self):
        self.state = None
        self.token = None

    def start_auth(self):
        self.state = str(random.random())  # ❌ Insecure
        url = f"{AUTH_URL}?state={self.state}"
        return url

    def handle_callback(self, code, state):
        if state == self.state:  # ❌ Timing attack
            # Exchange code...
            pass
```

**After**:
```python
from agno.cli.oauth_flow import OAuthFlowHandler, ProviderConfig

handler = OAuthFlowHandler(
    provider=ProviderConfig.google(client_id, client_secret, scopes),
    flow_type=OAuthFlowType.AUTHORIZATION_CODE_PKCE
)

# Secure by default!
auth_url = handler.build_authorization_url()
token = handler.handle_callback({"code": code, "state": state})
```

---

### 2. Add Token Auto-Refresh

**Before**:
```python
def call_api(self):
    # Manual token management
    if self.token_expired():
        self.refresh_token()

    headers = {"Authorization": f"Bearer {self.access_token}"}
    response = requests.get(API_URL, headers=headers)

    if response.status_code == 401:
        # Token expired during request
        self.refresh_token()
        # Retry...
```

**After**:
```python
def call_api(self):
    # Automatic refresh!
    token = handler.get_token()

    headers = {"Authorization": f"Bearer {token.access_token}"}
    response = requests.get(API_URL, headers=headers)
```

---

### 3. Add Pattern Analysis to CI/CD

```yaml
# .github/workflows/oauth-security-check.yml
name: OAuth Security Check

on: [push, pull_request]

jobs:
  security-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Analyze OAuth Patterns
        run: |
          python -c "
          from agno.cli.oauth_pattern_analyzer import OAuthPatternAnalyzer

          analyzer = OAuthPatternAnalyzer()
          result = analyzer.analyze_file('path/to/oauth_code.py')

          # Fail if critical anti-patterns found
          critical_issues = [
              ap for ap in result['anti_patterns']
              if ap.get('severity') == 'CRITICAL'
          ]

          if critical_issues:
              print('CRITICAL SECURITY ISSUES FOUND!')
              for issue in critical_issues:
                  print(f'- {issue[\"name\"]}: {issue[\"description\"]}')
              exit(1)
          "
```

---

## Security Best Practices

### 1. Production Checklist

- [ ] Use PKCE for public clients
- [ ] Always validate state parameter
- [ ] Use `secrets` module for random generation
- [ ] Use `secrets.compare_digest()` for comparisons
- [ ] Store client secrets in environment variables
- [ ] Use HTTPS for redirect URIs
- [ ] Implement token expiry checks with buffer
- [ ] Enable automatic token refresh
- [ ] Log authentication events
- [ ] Validate scopes before API calls
- [ ] Handle token revocation gracefully
- [ ] Implement rate limiting
- [ ] Use short-lived access tokens
- [ ] Rotate refresh tokens when possible

### 2. Token Storage

```python
# ✅ Secure token storage
import keyring

# Store
token_data = handler.export_state()
keyring.set_password("myapp", "oauth_token", json.dumps(token_data))

# Retrieve
token_data_json = keyring.get_password("myapp", "oauth_token")
if token_data_json:
    handler.import_state(json.loads(token_data_json))
```

### 3. Error Handling

```python
from agno.cli.oauth_flow import (
    OAuthError,
    InvalidStateError,
    TokenExpiredError
)

try:
    token = handler.handle_callback(params)
except InvalidStateError:
    # CSRF attack attempt or session timeout
    logger.warning("State validation failed")
    return redirect_to_login()
except TokenExpiredError:
    # Token expired and can't refresh
    logger.info("Token expired, re-authenticating")
    return redirect_to_auth()
except OAuthError as e:
    # General OAuth error
    logger.error(f"OAuth error: {e}")
    return show_error_page()
```

---

## Quick Reference

### Common Tasks

#### Initialize OAuth Handler
```python
from agno.cli.oauth_flow import OAuthFlowHandler, ProviderConfig, OAuthFlowType

provider = ProviderConfig.google(
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    scopes=["email", "profile"]
)

handler = OAuthFlowHandler(provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)
```

#### Start Authorization
```python
auth_url = handler.build_authorization_url()
# Redirect user to auth_url
```

#### Handle Callback
```python
token = handler.handle_callback({
    "code": request.args.get("code"),
    "state": request.args.get("state")
})
```

#### Get Valid Token
```python
token = handler.get_token()  # Auto-refreshes if needed
```

#### Analyze OAuth Code
```python
from agno.cli.oauth_pattern_analyzer import OAuthPatternAnalyzer

analyzer = OAuthPatternAnalyzer()
result = analyzer.analyze_file("oauth_code.py")
recommendations = analyzer.generate_recommendations(result)
```

---

## Additional Resources

- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-19
**Maintainer**: Agno Framework Team

# OAuth 2.0 FSA Handler & Pattern Analyzer

Production-ready OAuth 2.0 Finite State Automaton with automated pattern discovery for the Agno Framework.

## Features

### OAuth Flow Handler (FSA)
- ✅ **Multiple Flow Types**: Authorization Code, PKCE, Implicit, Client Credentials, Refresh Token
- ✅ **State Machine**: Comprehensive FSA with validated state transitions
- ✅ **Security**: PKCE support, timing-safe comparisons, cryptographic random generation
- ✅ **Provider Configs**: Pre-built configurations for Google, GitHub, Microsoft
- ✅ **Token Management**: Auto-refresh, expiry checks with buffer, scope validation
- ✅ **Callback Handling**: Secure state validation, error handling
- ✅ **State Persistence**: Export/import for session management
- ✅ **Production Ready**: Comprehensive logging, error handling, thread-safe design

### Pattern Analyzer
- ✅ **AST Parsing**: Extract OAuth patterns from Python code
- ✅ **Pattern Discovery**: Identify state transitions, error handling, token management
- ✅ **Anti-Pattern Detection**: Find security vulnerabilities and bad practices
- ✅ **Similarity Analysis**: Cluster similar patterns using vector embeddings
- ✅ **Recommendations**: Generate refactoring suggestions
- ✅ **Statistical Analysis**: Code metrics and pattern frequency

## Quick Start

### 1. Basic OAuth Flow

```python
from agno.cli.oauth_flow import OAuthFlowHandler, ProviderConfig, OAuthFlowType
import os

# Configure provider
provider = ProviderConfig.google(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=["email", "profile"]
)

# Create handler with PKCE
handler = OAuthFlowHandler(provider, OAuthFlowType.AUTHORIZATION_CODE_PKCE)

# Start authentication
auth_url = handler.build_authorization_url()
print(f"Visit: {auth_url}")

# Handle callback (after user authorizes)
token = handler.handle_callback({
    "code": "authorization_code_from_callback",
    "state": "state_from_callback"
})

# Use token (auto-refreshes if expired)
valid_token = handler.get_token()
```

### 2. Pattern Analysis

```python
from agno.cli.oauth_pattern_analyzer import OAuthPatternAnalyzer

# Analyze OAuth implementation
analyzer = OAuthPatternAnalyzer()
result = analyzer.analyze_file("my_oauth_code.py")

# Check for anti-patterns
for anti_pattern in result["anti_patterns"]:
    print(f"⚠️  {anti_pattern['name']}: {anti_pattern['description']}")

# Get recommendations
recommendations = analyzer.generate_recommendations(result)
for rec in recommendations:
    print(f"💡 {rec['title']}: {rec['recommendation']}")

# Generate pattern library
library = analyzer.generate_pattern_library()
```

### 3. Working Examples

```python
# See oauth_examples.py for complete examples:

# Example 1: Google OAuth with PKCE
from agno.cli.oauth_examples import GoogleOAuthExample
google = GoogleOAuthExample(client_id, client_secret)
auth_url = google.start_authentication()
token = google.handle_callback(code, state)

# Example 2: GitHub OAuth
from agno.cli.oauth_examples import GitHubOAuthExample
github = GitHubOAuthExample(client_id, client_secret, scopes=["repo"])
auth_url = github.get_authorization_url()

# Example 3: Auto-Refresh Pattern
from agno.cli.oauth_examples import TokenAutoRefreshExample
manager = TokenAutoRefreshExample(handler)
result = manager.execute_with_retry(api_call_function)
```

## Installation

```bash
# OAuth handler is part of the agno CLI package
# No additional dependencies required - uses Python stdlib only
```

## Architecture

### State Machine Diagram

```
┌─────────┐
│ INITIAL │
└────┬────┘
     │
     ▼
┌──────────────────────────┐
│ AUTHORIZATION_REQUESTED  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────┐
│ WAITING_FOR_CALLBACK │
└──────────┬───────────┘
           │
           ▼
┌──────────────────┐
│ EXCHANGING_CODE  │
└──────────┬───────┘
           │
           ▼
┌────────────────┐     ┌───────────────────┐
│ AUTHENTICATED  │◄────┤ REFRESHING_TOKEN  │
└────────┬───────┘     └───────────────────┘
         │
         ▼
┌─────────┐
│ EXPIRED │
└─────────┘

(Any state can transition to ERROR, which can reset to INITIAL)
```

### Component Structure

```
agno/cli/
├── oauth_flow.py              # Core FSA handler
├── oauth_pattern_analyzer.py  # Pattern discovery & analysis
├── oauth_examples.py          # Working examples
├── OAUTH_PATTERN_LIBRARY.md   # Pattern library & best practices
└── OAUTH_README.md            # This file

tests/unit/cli/
├── test_oauth_flow.py         # OAuth handler tests (500+ lines)
└── test_oauth_pattern_analyzer.py  # Pattern analyzer tests
```

## Supported Providers

### Google OAuth
```python
provider = ProviderConfig.google(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["email", "profile", "https://www.googleapis.com/auth/gmail.readonly"]
)
# Supports: PKCE ✅, Refresh ✅
```

### GitHub OAuth
```python
provider = ProviderConfig.github(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["repo", "user", "gist"]
)
# Supports: PKCE ❌, Refresh ❌
```

### Microsoft OAuth
```python
provider = ProviderConfig.microsoft(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["User.Read", "Mail.Read"],
    tenant="common"
)
# Supports: PKCE ✅, Refresh ✅
```

### Custom Provider
```python
provider = ProviderConfig(
    name="custom",
    authorization_endpoint="https://provider.com/oauth/authorize",
    token_endpoint="https://provider.com/oauth/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["custom_scope"],
    supports_pkce=True,
    supports_refresh=True
)
```

## Flow Types

| Flow Type | Use Case | Security |
|-----------|----------|----------|
| `AUTHORIZATION_CODE` | Server-side web apps | High |
| `AUTHORIZATION_CODE_PKCE` | SPAs, mobile, desktop apps | Very High |
| `IMPLICIT` | Legacy (deprecated) | Low |
| `CLIENT_CREDENTIALS` | Machine-to-machine | High |
| `REFRESH_TOKEN` | Token renewal | High |

## Security Features

### 1. PKCE (Proof Key for Code Exchange)
Prevents authorization code interception attacks.

```python
# Automatic PKCE with OAuthFlowType.AUTHORIZATION_CODE_PKCE
verifier, challenge = context.generate_pkce_challenge()
# SHA256-based challenge automatically included in auth URL
```

### 2. State Parameter Protection
CSRF protection with cryptographically secure random generation.

```python
# Automatic state generation and validation
state = context.generate_state()  # secrets.token_urlsafe(32)
is_valid = context.validate_state(received_state)  # timing-safe comparison
```

### 3. Token Expiry Buffer
Prevents using tokens that expire during requests.

```python
# 60-second buffer by default
@property
def is_expired(self) -> bool:
    return time.time() >= (self.issued_at + self.expires_in - 60)
```

### 4. Timing-Safe Comparisons
Prevents timing attacks on security-critical comparisons.

```python
# Uses secrets.compare_digest() internally
return secrets.compare_digest(expected, received)
```

## Pattern Library

### Known Patterns (5)

1. **PKCE Generation** (`pkce_gen_001`) - Cryptographically secure challenge
2. **State Validation** (`state_val_001`) - Timing-safe comparison
3. **Token Expiry Check** (`token_exp_001`) - Buffer for clock skew
4. **Auto Refresh** (`token_ref_001`) - Transparent token renewal
5. **FSM Validation** (`fsm_val_001`) - State transition validation

### Anti-Patterns (6)

1. **Plain State Comparison** (`anti_001`) - Timing attack vulnerability
2. **No PKCE** (`anti_002`) - Authorization code interception risk
3. **Hardcoded Secrets** (`anti_003`) - Credential exposure
4. **Missing State** (`anti_004`) - CSRF vulnerability
5. **Insecure Random** (`anti_005`) - Predictable tokens
6. **No Expiry Check** (`anti_006`) - Expired token usage

See [OAUTH_PATTERN_LIBRARY.md](OAUTH_PATTERN_LIBRARY.md) for complete documentation.

## Testing

### Run Tests

```bash
# Run all OAuth tests
pytest libs/agno/tests/unit/cli/test_oauth_flow.py -v

# Run pattern analyzer tests
pytest libs/agno/tests/unit/cli/test_oauth_pattern_analyzer.py -v

# Run with coverage
pytest libs/agno/tests/unit/cli/ --cov=agno.cli.oauth_flow --cov=agno.cli.oauth_pattern_analyzer
```

### Test Coverage

- OAuth Flow Handler: 50+ test cases
- Pattern Analyzer: 30+ test cases
- All flow types tested
- All providers tested
- Security features tested
- Edge cases covered

## Usage Examples

### Example 1: Complete Google Authentication

```python
from agno.cli.oauth_examples import GoogleOAuthExample

# Initialize
google = GoogleOAuthExample(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"]
)

# Get authorization URL
auth_url = google.start_authentication()
print(f"Visit: {auth_url}")

# Handle callback (after user clicks "allow")
token = google.handle_callback(
    authorization_code=request.args.get("code"),
    state=request.args.get("state")
)

# Use token for API calls
gmail_token = google.get_valid_token()
headers = {"Authorization": f"Bearer {gmail_token.access_token}"}
response = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=headers)
```

### Example 2: Token Auto-Refresh

```python
from agno.cli.oauth_examples import TokenAutoRefreshExample

# Create auto-refresh manager
manager = TokenAutoRefreshExample(oauth_handler)

# Define API call
def fetch_emails():
    token = oauth_handler.get_token()
    return requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {token.access_token}"}
    ).json()

# Execute with automatic retry on token expiry
emails = manager.execute_with_retry(fetch_emails, max_retries=2)
```

### Example 3: Pattern Analysis in CI/CD

```python
from agno.cli.oauth_pattern_analyzer import OAuthPatternAnalyzer

# Analyze OAuth implementation
analyzer = OAuthPatternAnalyzer()
result = analyzer.analyze_file("oauth_implementation.py")

# Check for critical issues
critical_issues = [
    ap for ap in result["anti_patterns"]
    if ap.get("severity") == "CRITICAL"
]

if critical_issues:
    print("❌ CRITICAL SECURITY ISSUES FOUND:")
    for issue in critical_issues:
        print(f"  - {issue['name']}")
        print(f"    Location: {issue['locations']}")
        print(f"    Fix: {issue['metadata'].get('recommendation')}")
    exit(1)

print("✅ No critical security issues found")
```

## API Reference

### OAuthFlowHandler

```python
class OAuthFlowHandler:
    def __init__(provider: ProviderConfig, flow_type: OAuthFlowType)
    def build_authorization_url(additional_params: Dict = None) -> str
    def handle_callback(callback_params: Dict) -> OAuthToken
    def exchange_code_for_token(code: str) -> OAuthToken
    def refresh_access_token() -> OAuthToken
    def get_token() -> OAuthToken
    def validate_scopes(required_scopes: List[str]) -> bool
    def export_state() -> Dict
    def import_state(state_data: Dict)
    def reset()
```

### OAuthPatternAnalyzer

```python
class OAuthPatternAnalyzer:
    def __init__()
    def analyze_file(file_path: str) -> Dict
    def cluster_patterns(similarity_threshold: float = 0.7) -> List[PatternCluster]
    def generate_recommendations(analysis_results: Dict) -> List[Dict]
    def generate_pattern_library() -> Dict
```

## Best Practices

### ✅ DO

- Use `AUTHORIZATION_CODE_PKCE` for public clients
- Store secrets in environment variables
- Use automatic token refresh
- Validate state parameters
- Check token expiry with buffer
- Use HTTPS for redirect URIs
- Log authentication events
- Handle errors gracefully

### ❌ DON'T

- Hardcode client secrets
- Use `==` for state comparison (use `secrets.compare_digest()`)
- Use `random.random()` for security tokens (use `secrets.token_urlsafe()`)
- Skip state parameter validation
- Ignore token expiry
- Use deprecated implicit flow
- Store tokens in localStorage (web apps)

## Troubleshooting

### Issue: "Invalid state parameter"
**Cause**: State mismatch or timing issue
**Fix**: Ensure state is passed correctly from authorization URL to callback

### Issue: "Token expired and cannot be refreshed"
**Cause**: No refresh token or provider doesn't support refresh
**Fix**: Re-authenticate or use provider that supports refresh tokens

### Issue: "PKCE not supported"
**Cause**: Provider doesn't support PKCE (e.g., GitHub)
**Fix**: Use `AUTHORIZATION_CODE` flow instead

### Issue: "Insufficient scopes"
**Cause**: Requested scopes not granted
**Fix**: Check scope validation and request correct scopes

## Performance

- State machine operations: O(1)
- Pattern analysis: O(n) where n = lines of code
- Similarity calculation: O(m²) where m = number of patterns
- Memory usage: Minimal (stateless operations)

## Contributing

See [OAUTH_PATTERN_LIBRARY.md](OAUTH_PATTERN_LIBRARY.md) for:
- Pattern submission guidelines
- Anti-pattern reporting
- Documentation standards

## License

Part of the Agno Framework - see main repository license.

## Support

For issues, questions, or contributions:
- GitHub Issues: [agno/issues](https://github.com/agno/agno/issues)
- Documentation: [OAUTH_PATTERN_LIBRARY.md](OAUTH_PATTERN_LIBRARY.md)

---

**Version**: 1.0
**Last Updated**: 2025-11-19
**Status**: Production Ready

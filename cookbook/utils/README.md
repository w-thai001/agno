# Rate Limiter Usage Guide

This guide demonstrates how to use Agno's production-ready rate limiting utilities.

## Overview

Agno provides two rate limiting implementations:

1. **TokenBucketRateLimiter** - Token bucket algorithm with burst support
2. **SlidingWindowRateLimiter** - Sliding window for precise rate tracking

Both implementations use Redis for distributed rate limiting, making them suitable for production environments with multiple servers.

## Installation

```bash
pip install agno[redis]
```

## Quick Start

```python
from agno.utils.rate_limiter import TokenBucketRateLimiter

# Initialize the rate limiter
limiter = TokenBucketRateLimiter(
    redis_client="redis://localhost:6379/0",
    default_max_requests=100,
    default_time_window_seconds=60
)

# Check if request should be allowed
result = limiter.allow_request("user_123")

if result.allow_request:
    print(f"Request allowed! Remaining: {result.remaining_tokens}")
    # Process the request
else:
    print(f"Rate limited! Retry after: {result.retry_after_seconds}s")
    # Return 429 Too Many Requests
```

## Running the Examples

### Prerequisites

1. **Start Redis** (using Docker):
   ```bash
   docker run -d -p 6379:6379 redis:7.2.1
   ```

2. **Install dependencies**:
   ```bash
   pip install agno[redis]
   ```

### Run the Example Script

```bash
python cookbook/utils/rate_limiter_example.py
```

This will run all examples demonstrating:
- Basic rate limiting
- API endpoint protection
- Tiered rate limits (free/basic/premium)
- Sliding window rate limiting
- Burst allowances
- Multi-token requests
- Production integration patterns
- Monitoring and metrics

## Features

### 1. Token Bucket Algorithm

The token bucket algorithm allows for:
- **Burst traffic** - Clients can consume multiple tokens at once if available
- **Smooth rate limiting** - Tokens refill at a constant rate
- **Fairness** - Each client gets their own bucket

**When to use**: Great for APIs where you want to allow bursts of traffic while maintaining an average rate limit.

### 2. Sliding Window

The sliding window algorithm provides:
- **Precise tracking** - No edge effects at window boundaries
- **Accurate limits** - Counts exact requests in the time window
- **Distributed safety** - Works across multiple servers

**When to use**: Best when you need precise rate limiting without allowing bursts at window boundaries.

### 3. Distributed Rate Limiting

Both implementations use Redis with Lua scripts for:
- **Atomic operations** - No race conditions
- **Distributed consistency** - Works across multiple servers
- **Memory efficiency** - Automatic cleanup of old data

### 4. Production Ready

Features for production use:
- **Fail-open behavior** - On Redis errors, allows requests (prevents service disruption)
- **Configurable limits** - Per-client custom limits
- **Multi-token requests** - Support for expensive operations
- **Monitoring** - Get client info and metrics
- **Context manager** - Automatic cleanup

## API Reference

### TokenBucketRateLimiter

#### Constructor

```python
TokenBucketRateLimiter(
    redis_client: str | Redis = None,
    key_prefix: str = "rate_limit",
    default_max_requests: int = 100,
    default_time_window_seconds: int = 60
)
```

**Parameters**:
- `redis_client`: Redis connection URL or client instance
- `key_prefix`: Prefix for Redis keys (useful for namespacing)
- `default_max_requests`: Default bucket capacity
- `default_time_window_seconds`: Default refill period

#### Methods

**allow_request()**

```python
def allow_request(
    client_id: str,
    max_requests: Optional[int] = None,
    time_window_seconds: Optional[int] = None,
    tokens_requested: int = 1
) -> RateLimitResult
```

Check if a request should be allowed.

**Parameters**:
- `client_id`: Unique identifier (user ID, IP, API key, etc.)
- `max_requests`: Override default limit
- `time_window_seconds`: Override default window
- `tokens_requested`: Number of tokens to consume (default: 1)

**Returns**: `RateLimitResult` with:
- `allow_request`: bool - Whether to allow the request
- `remaining_tokens`: int - Tokens remaining in bucket
- `retry_after_seconds`: float - Seconds until next token (if denied)

**reset_client()**

```python
def reset_client(client_id: str) -> bool
```

Reset rate limit for a client (useful for manual overrides).

**get_client_info()**

```python
def get_client_info(client_id: str) -> Optional[Tuple[float, float]]
```

Get current token count and last refill time.

### SlidingWindowRateLimiter

Same API as `TokenBucketRateLimiter` but without `tokens_requested` parameter (always consumes 1 request per call).

## Usage Patterns

### Pattern 1: API Endpoint Protection

```python
from agno.utils.rate_limiter import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter()

def api_endpoint(user_id: str):
    result = limiter.allow_request(user_id)

    if not result.allow_request:
        return {
            "error": "Rate limit exceeded",
            "retry_after": result.retry_after_seconds
        }, 429

    # Process request
    return {"data": "..."}, 200
```

### Pattern 2: Different Limits per User Tier

```python
TIER_LIMITS = {
    "free": 10,
    "basic": 100,
    "premium": 1000
}

def check_limit(user_id: str, tier: str):
    max_requests = TIER_LIMITS.get(tier, 10)
    return limiter.allow_request(
        f"{tier}:{user_id}",
        max_requests=max_requests,
        time_window_seconds=60
    )
```

### Pattern 3: Expensive Operations

```python
# Charge more tokens for expensive operations
result = limiter.allow_request(
    user_id,
    tokens_requested=10  # This operation costs 10 tokens
)
```

### Pattern 4: Flask Integration

```python
from flask import Flask, request
from agno.utils.rate_limiter import TokenBucketRateLimiter

app = Flask(__name__)
limiter = TokenBucketRateLimiter()

@app.before_request
def check_rate_limit():
    client_id = request.headers.get('X-API-Key') or request.remote_addr
    result = limiter.allow_request(client_id)

    if not result.allow_request:
        return {
            "error": "Rate limit exceeded"
        }, 429, {
            "Retry-After": str(int(result.retry_after_seconds))
        }
```

### Pattern 5: FastAPI Integration

```python
from fastapi import FastAPI, Request, HTTPException
from agno.utils.rate_limiter import TokenBucketRateLimiter

app = FastAPI()
limiter = TokenBucketRateLimiter()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.headers.get('X-API-Key') or request.client.host
    result = limiter.allow_request(client_id)

    if not result.allow_request:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(result.retry_after_seconds))}
        )

    response = await call_next(request)
    response.headers['X-RateLimit-Remaining'] = str(result.remaining_tokens)
    return response
```

## Best Practices

### 1. Choose the Right Algorithm

- **Token Bucket**: Use when you want to allow bursts while maintaining average rate
- **Sliding Window**: Use when you need precise limits without burst allowance

### 2. Client Identification

Choose appropriate client identifiers:
- **User ID**: For authenticated APIs
- **API Key**: For API key-based authentication
- **IP Address**: For public endpoints (be careful with shared IPs)
- **Combination**: e.g., `f"{user_id}:{endpoint}"` for per-endpoint limits

### 3. Error Handling

The rate limiter fails open on Redis errors to prevent service disruption:

```python
result = limiter.allow_request(client_id)
# If Redis is down, result.allow_request will be True
```

Always monitor Redis health in production.

### 4. Set Appropriate Limits

Consider:
- **User tier**: Different limits for different subscription levels
- **Endpoint cost**: More expensive operations consume more tokens
- **Business requirements**: Balance user experience with resource protection

### 5. Add Rate Limit Headers

Help clients manage their usage:

```python
response.headers['X-RateLimit-Limit'] = str(max_requests)
response.headers['X-RateLimit-Remaining'] = str(result.remaining_tokens)
response.headers['X-RateLimit-Reset'] = str(result.retry_after_seconds)
```

### 6. Monitoring

Monitor rate limiting metrics:
- Number of rate-limited requests
- Top rate-limited clients
- Redis connection health
- Average remaining tokens

## Troubleshooting

### Redis Connection Errors

```python
# Error: redis.exceptions.ConnectionError
```

**Solution**: Ensure Redis is running and accessible:
```bash
docker run -d -p 6379:6379 redis:7.2.1
```

### Import Errors

```python
# ImportError: redis-py is required
```

**Solution**: Install Redis support:
```bash
pip install agno[redis]
```

### High Memory Usage

If Redis memory usage is high, check TTL settings. The rate limiter automatically sets TTL to `2 * time_window` to clean up old data.

## Performance Considerations

### Redis Connection Pooling

For high-traffic applications, use connection pooling:

```python
import redis

pool = redis.ConnectionPool.from_url('redis://localhost:6379/0')
client = redis.Redis(connection_pool=pool)

limiter = TokenBucketRateLimiter(redis_client=client)
```

### Lua Scripts

Both implementations use Lua scripts for atomic operations, which means:
- No race conditions
- Single round-trip to Redis
- Better performance than multiple commands

### Memory Usage

- **Token Bucket**: ~2 hash fields per client (~100 bytes)
- **Sliding Window**: ~50 bytes per request (stored in sorted set)

For 1M active users with sliding window (100 req/min):
- Memory usage: ~5GB

Consider using token bucket for better memory efficiency.

## Additional Resources

- [Rate Limiting Algorithms Explained](https://en.wikipedia.org/wiki/Token_bucket)
- [Redis Lua Scripting](https://redis.io/docs/manual/programmability/eval-intro/)
- [API Rate Limiting Best Practices](https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-07.html)

## Support

For issues or questions:
- GitHub Issues: https://github.com/agno-ai/agno/issues
- Documentation: https://docs.agno.com

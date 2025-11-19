# Rate Limiting Examples for Agno Framework

This directory contains examples demonstrating how to use the rate limiting FSA patterns in the Agno Framework.

## Examples

### 1. Basic Token Bucket (`01_basic_token_bucket.py`)

Demonstrates the fundamentals of token bucket rate limiting:
- Creating a token bucket limiter
- Making requests and handling rate limits
- Understanding token refill mechanics
- Monitoring metrics and state transitions

**Run**:
```bash
python 01_basic_token_bucket.py
```

### 2. Sliding Window Per-User (`02_sliding_window_per_user.py`)

Shows how to implement per-user rate limiting:
- Managing multiple rate limiters for different users
- Sliding window algorithm in action
- Independent rate limits per user
- Request expiration over time

**Run**:
```bash
python 02_sliding_window_per_user.py
```

### 3. Agent with Rate Limiting (`03_agent_with_rate_limiting.py`)

Integrates rate limiting with Agno agents:
- Rate limiting model API calls
- Rate limiting tool executions
- Using pre-hooks for rate limit enforcement
- Handling rate limit exceptions

**Run**:
```bash
export OPENAI_API_KEY="your-key-here"
python 03_agent_with_rate_limiting.py
```

## Rate Limiting Algorithms

The Agno Framework provides four rate limiting patterns:

### Token Bucket
- **File**: `agno.rate_limit.TokenBucketRateLimiter`
- **Best For**: API rate limiting, handling bursts
- **Example**: 100 requests per minute with burst capacity

```python
from agno.rate_limit import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(
    rate_limit_id="api",
    capacity=100,
    refill_rate=100/60,  # 100 per minute
)

if limiter.allow_request():
    # Make API call
    pass
```

### Sliding Window
- **File**: `agno.rate_limit.SlidingWindowRateLimiter`
- **Best For**: Precise rate limiting, user quotas
- **Example**: 100 requests per hour per user

```python
from agno.rate_limit import SlidingWindowRateLimiter

limiter = SlidingWindowRateLimiter(
    rate_limit_id="user_123",
    max_requests=100,
    window_size=3600,  # 1 hour
)
```

### Fixed Window
- **File**: `agno.rate_limit.FixedWindowRateLimiter`
- **Best For**: Simple limits, billing periods
- **Example**: 1000 requests per day

```python
from agno.rate_limit import FixedWindowRateLimiter

limiter = FixedWindowRateLimiter(
    rate_limit_id="daily_limit",
    max_requests=1000,
    window_size=86400,  # 24 hours
)
```

### Distributed (Redis-backed)
- **File**: `agno.rate_limit.DistributedRateLimiter`
- **Best For**: Multi-server deployments, global limits
- **Example**: Global rate limit across all servers

```python
import redis
from agno.rate_limit import DistributedRateLimiter, DistributedAlgorithm

redis_client = redis.Redis(host='localhost', port=6379)

limiter = DistributedRateLimiter(
    rate_limit_id="global_api",
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.TOKEN_BUCKET,
    capacity=10000,
    refill_rate=10000/60,
)
```

## Common Patterns

### Pattern 1: Pre-Hook for Tool Rate Limiting

```python
from agno.tools import Function
from agno.rate_limit import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(...)

def rate_limit_hook(function_call):
    if not limiter.allow_request():
        raise Exception("Rate limited")

tool = Function.from_callable(my_function)
tool.pre_hook = rate_limit_hook
```

### Pattern 2: Per-User Rate Limiting

```python
from typing import Dict
from agno.rate_limit import SlidingWindowRateLimiter

class UserLimiter:
    def __init__(self):
        self.limiters: Dict[str, SlidingWindowRateLimiter] = {}

    def allow_request(self, user_id: str) -> bool:
        if user_id not in self.limiters:
            self.limiters[user_id] = SlidingWindowRateLimiter(
                rate_limit_id=user_id,
                max_requests=100,
                window_size=3600,
            )
        return self.limiters[user_id].allow_request()
```

### Pattern 3: Graceful Degradation

```python
from agno.rate_limit import RateLimitExceeded

try:
    if limiter.allow_request():
        result = expensive_operation()
    else:
        raise RateLimitExceeded("Rate limited")
except RateLimitExceeded as e:
    # Option 1: Return cached result
    result = get_cached_result()

    # Option 2: Queue for later
    queue.enqueue(operation, delay=e.retry_after)

    # Option 3: Return error
    return {"error": str(e)}
```

## Monitoring and Metrics

All rate limiters provide detailed metrics:

```python
metrics = limiter.get_metrics()

print(f"Total Requests: {metrics['total_requests']}")
print(f"Allowed: {metrics['allowed_requests']}")
print(f"Denied: {metrics['denied_requests']}")
print(f"Denial Rate: {metrics['denial_rate']:.1%}")
print(f"Utilization: {metrics['utilization']:.1%}")
print(f"Current State: {metrics['current_state']}")
```

## FSA States

All rate limiters follow this state machine:

- `AVAILABLE`: Under limit, requests proceed normally
- `WARNING`: >80% capacity used, approaching limit
- `RECOVERING`: Capacity recovering (tokens refilling, requests expiring)
- `LIMITED`: Rate limit exceeded, requests blocked

## Additional Resources

- **Documentation**: `docs/rate_limiting_patterns.md`
- **FSA Analysis**: `docs/fsa_pattern_analysis.md`
- **Source Code**: `libs/agno/agno/rate_limit/`

## Testing

Each rate limiter includes comprehensive tests:

```bash
# Run rate limiter tests
pytest libs/agno/tests/rate_limit/

# Run specific algorithm tests
pytest libs/agno/tests/rate_limit/test_token_bucket.py
pytest libs/agno/tests/rate_limit/test_sliding_window.py
pytest libs/agno/tests/rate_limit/test_fixed_window.py
pytest libs/agno/tests/rate_limit/test_distributed.py
```

## Contributing

When adding new rate limiting patterns:

1. Follow the FSA design pattern (inherit from `RateLimiter`)
2. Implement all abstract methods (`allow_request`, `get_retry_after`, `reset`)
3. Use the standard state machine (`RateLimitState`)
4. Track metrics using `RateLimitMetrics`
5. Add comprehensive examples and tests
6. Update documentation

## Questions?

- Check the main documentation: `docs/rate_limiting_patterns.md`
- See FSA pattern analysis: `docs/fsa_pattern_analysis.md`
- Review the source code: `libs/agno/agno/rate_limit/`

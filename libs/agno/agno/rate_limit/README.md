# Rate Limiting FSA Module

Production-ready rate limiting patterns for the Agno Framework, implemented as Finite State Automata (FSA).

## Quick Start

```python
from agno.rate_limit import TokenBucketRateLimiter

# Create rate limiter
limiter = TokenBucketRateLimiter(
    rate_limit_id="my_api",
    capacity=100,          # 100 tokens max
    refill_rate=100/60,    # 100 tokens per minute
)

# Use in your code
if limiter.allow_request():
    # Request allowed
    make_api_call()
else:
    # Rate limited
    retry_after = limiter.get_retry_after()
    print(f"Rate limited, retry after {retry_after}s")
```

## Available Limiters

### TokenBucketRateLimiter
**File**: `token_bucket.py`

Best for: API rate limiting, burst handling

```python
from agno.rate_limit import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(
    rate_limit_id="openai",
    capacity=100,
    refill_rate=100/60,  # 100/minute
)
```

### SlidingWindowRateLimiter
**File**: `sliding_window.py`

Best for: Precise rate limiting, user quotas

```python
from agno.rate_limit import SlidingWindowRateLimiter

limiter = SlidingWindowRateLimiter(
    rate_limit_id="user_123",
    max_requests=100,
    window_size=3600,  # 1 hour
)
```

### FixedWindowRateLimiter
**File**: `fixed_window.py`

Best for: Simple limits, billing periods

```python
from agno.rate_limit import FixedWindowRateLimiter

limiter = FixedWindowRateLimiter(
    rate_limit_id="daily",
    max_requests=1000,
    window_size=86400,  # 24 hours
)
```

### DistributedRateLimiter
**File**: `distributed.py`

Best for: Multi-server deployments, global limits

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

## FSA States

All rate limiters implement this state machine:

```
[AVAILABLE] → [WARNING] → [LIMITED]
     ↑            ↑            ↓
     └──refill────┴──refill────┘
```

- **AVAILABLE**: Under limit (< 80% utilized)
- **WARNING**: Approaching limit (80-100% utilized)
- **LIMITED**: Rate limit exceeded
- **RECOVERING**: Capacity recovering

## Common Methods

All rate limiters implement:

```python
# Check if request allowed
allowed: bool = limiter.allow_request(tokens=1.0)

# Get time until next request possible
retry_after: Optional[float] = limiter.get_retry_after()

# Reset the limiter
limiter.reset()

# Get comprehensive metrics
metrics: dict = limiter.get_metrics()
```

## Metrics

All limiters track:

```python
{
    "total_requests": int,
    "allowed_requests": int,
    "denied_requests": int,
    "current_capacity": float,
    "max_capacity": float,
    "utilization": float,      # 0.0 to 1.0
    "denial_rate": float,      # 0.0 to 1.0
    "current_state": str,
    "last_request_time": float,
}
```

## Exception Handling

```python
from agno.rate_limit import RateLimitExceeded

limiter = TokenBucketRateLimiter(
    rate_limit_id="api",
    capacity=100,
    refill_rate=100/60,
    raise_on_limit=True,  # Raise exception when limited
)

try:
    limiter.allow_request()
    make_api_call()
except RateLimitExceeded as e:
    print(f"Rate limited: {e}")
    print(f"Retry after: {e.retry_after}s")
    print(f"State: {e.current_state}")
```

## Integration with Agno

### With Agents

```python
from agno.agent import Agent
from agno.rate_limit import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(...)

agent = Agent(...)

def run_with_rate_limit(message: str):
    if not limiter.allow_request():
        return f"Rate limited, retry after {limiter.get_retry_after()}s"

    return agent.run(message)
```

### With Tools

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

### With Workflows

```python
from agno.workflow import Workflow
from agno.rate_limit import TokenBucketRateLimiter

class RateLimitedWorkflow(Workflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.limiter = TokenBucketRateLimiter(...)

    def run(self, **kwargs):
        if not self.limiter.allow_request():
            return RunResponse(
                content=f"Rate limited: {self.limiter.get_retry_after()}s"
            )

        return super().run(**kwargs)
```

## Algorithm Comparison

| Algorithm | Memory | Time | Best For |
|-----------|--------|------|----------|
| Token Bucket | O(1) | O(1) | API limits, bursts |
| Sliding Window | O(N) | O(log N) | Precise limits |
| Fixed Window | O(1) | O(1) | Simple limits |
| Distributed | Varies | O(1) or O(log N) | Multi-server |

## Examples

See `cookbook/rate_limiting/` for complete examples:

- `01_basic_token_bucket.py` - Basic usage
- `02_sliding_window_per_user.py` - Per-user limits
- `03_agent_with_rate_limiting.py` - Agent integration

## Documentation

- **Detailed Guide**: `docs/rate_limiting_patterns.md`
- **FSA Analysis**: `docs/fsa_pattern_analysis.md`
- **Examples**: `cookbook/rate_limiting/`

## Testing

```bash
pytest libs/agno/tests/rate_limit/
```

## License

Same as Agno Framework

# Rate Limiting FSA Patterns for Agno Framework

**Version**: 1.0
**Author**: Agno Framework
**Date**: 2025-11-19

---

## Overview

This document describes the rate limiting FSA (Finite State Automaton) patterns implemented for the Agno Framework. These patterns provide reusable, production-ready rate limiting solutions for API calls, tool executions, and multi-agent workflows.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Rate Limiting Algorithms](#rate-limiting-algorithms)
3. [Usage Examples](#usage-examples)
4. [FSA State Diagrams](#fsa-state-diagrams)
5. [Integration Patterns](#integration-patterns)
6. [Performance Considerations](#performance-considerations)
7. [Best Practices](#best-practices)

---

## Architecture

### Base Components

All rate limiters inherit from the `RateLimiter` base class and implement a common FSA interface:

```python
from agno.rate_limit.base import RateLimiter, RateLimitState, RateLimitExceeded

class RateLimiter(ABC):
    rate_limit_id: str
    current_state: RateLimitState
    metrics: RateLimitMetrics

    @abstractmethod
    def allow_request(self, tokens: float = 1.0) -> bool:
        """Check if request is allowed"""
        pass

    @abstractmethod
    def get_retry_after(self) -> Optional[float]:
        """Get time until next request"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset limiter state"""
        pass
```

### FSA States

All rate limiters use the following state machine:

```python
class RateLimitState(str, Enum):
    AVAILABLE = "available"    # Under limit, requests proceed
    WARNING = "warning"        # >80% utilized
    RECOVERING = "recovering"  # Capacity recovering
    LIMITED = "limited"        # Rate limit exceeded
```

### Metrics

All rate limiters track comprehensive metrics:

```python
@dataclass
class RateLimitMetrics:
    total_requests: int
    allowed_requests: int
    denied_requests: int
    current_capacity: float
    max_capacity: float

    @property
    def utilization(self) -> float:
        """Returns 0.0 to 1.0"""

    @property
    def denial_rate(self) -> float:
        """Returns 0.0 to 1.0"""
```

---

## Rate Limiting Algorithms

### 1. Token Bucket Algorithm

**File**: `libs/agno/agno/rate_limit/token_bucket.py`

**Best For**:
- Smooth rate limiting with bursts
- API rate limiting (e.g., 100 requests per minute)
- Variable request costs (some requests cost more tokens)

**How It Works**:
- Maintains a bucket of tokens
- Tokens refill at a constant rate
- Each request consumes tokens
- If bucket is empty, requests are denied

**Example**:
```python
from agno.rate_limit import TokenBucketRateLimiter

# Allow 100 requests per minute with bursts up to 100
limiter = TokenBucketRateLimiter(
    rate_limit_id="openai_api",
    capacity=100,           # Max burst
    refill_rate=100/60,     # 100 tokens per 60 seconds
)

# Check request
if limiter.allow_request():
    # Make API call
    response = model.generate(...)
else:
    retry_after = limiter.get_retry_after()
    print(f"Rate limited, retry after {retry_after:.2f}s")
```

**Variable Token Consumption**:
```python
# Cost more tokens for expensive requests
if limiter.allow_request(tokens=5.0):
    # Expensive operation consuming 5 tokens
    pass
```

**Dynamic Adjustment**:
```python
# Adjust capacity and refill rate at runtime
limiter.set_capacity(200)
limiter.set_refill_rate(200/60)
```

**Metrics**:
```python
metrics = limiter.get_metrics()
print(f"Utilization: {metrics['utilization']:.2%}")
print(f"Denial rate: {metrics['denial_rate']:.2%}")
print(f"Available tokens: {metrics['current_capacity']:.2f}")
```

---

### 2. Sliding Window Algorithm

**File**: `libs/agno/agno/rate_limit/sliding_window.py`

**Best For**:
- Accurate rate limiting without boundary issues
- User-facing rate limits (e.g., "100 requests per hour per user")
- When precision is critical

**How It Works**:
- Tracks requests in a continuously sliding time window
- Automatically expires old requests
- More accurate than fixed windows (no boundary issues)

**Example**:
```python
from agno.rate_limit import SlidingWindowRateLimiter

# Allow 100 requests per user per hour
limiter = SlidingWindowRateLimiter(
    rate_limit_id="user_123",
    max_requests=100,
    window_size=3600,  # 1 hour in seconds
)

if limiter.allow_request():
    # Process user request
    pass
else:
    retry_after = limiter.get_retry_after()
    print(f"User rate limited, retry after {retry_after:.2f}s")
```

**Check Current Usage**:
```python
current_count = limiter.get_current_count()
print(f"User has made {current_count}/100 requests in the last hour")

rps = limiter.get_requests_per_second()
print(f"Current rate: {rps:.2f} requests/second")
```

**Dynamic Adjustment**:
```python
# Upgrade user to premium tier
limiter.set_max_requests(1000)
limiter.set_window_size(3600)
```

---

### 3. Fixed Window Algorithm

**File**: `libs/agno/agno/rate_limit/fixed_window.py`

**Best For**:
- Simple rate limiting with minimal memory
- Billing periods (e.g., "1000 API calls per calendar month")
- When exact accuracy is not critical

**How It Works**:
- Divides time into fixed windows (e.g., per minute, per hour)
- Each window has a counter
- Counter resets at window boundaries

**Note**: Can allow up to 2x limit at window boundaries. Use SlidingWindowRateLimiter for more accuracy.

**Example**:
```python
from agno.rate_limit import FixedWindowRateLimiter

# Allow 1000 requests per hour
limiter = FixedWindowRateLimiter(
    rate_limit_id="api_key_456",
    max_requests=1000,
    window_size=3600,  # 1 hour
)

if limiter.allow_request():
    # Process request
    pass
```

**Check Time Until Reset**:
```python
time_until_reset = limiter.get_time_until_reset()
print(f"Window resets in {time_until_reset:.0f} seconds")

current_count = limiter.get_current_count()
print(f"Requests in current window: {current_count}/1000")
```

---

### 4. Distributed Rate Limiting (Redis-backed)

**File**: `libs/agno/agno/rate_limit/distributed.py`

**Best For**:
- Multi-server deployments
- Microservices architecture
- Global rate limits across all instances

**How It Works**:
- Uses Redis as shared state store
- Supports all three algorithms (token bucket, sliding window, fixed window)
- Atomic operations using Lua scripts
- Configurable fallback strategies

**Example**:
```python
import redis
from agno.rate_limit import DistributedRateLimiter, DistributedAlgorithm

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Token Bucket (distributed)
limiter = DistributedRateLimiter(
    rate_limit_id="global_api",
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.TOKEN_BUCKET,
    capacity=10000,
    refill_rate=10000/60,  # 10k per minute across all servers
)

if limiter.allow_request():
    # Process request
    pass
```

**Sliding Window (distributed)**:
```python
limiter = DistributedRateLimiter(
    rate_limit_id="user_789",
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.SLIDING_WINDOW,
    max_requests=100,
    window_size=60,
)
```

**Fixed Window (distributed)**:
```python
limiter = DistributedRateLimiter(
    rate_limit_id="tenant_abc",
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.FIXED_WINDOW,
    max_requests=1000,
    window_size=3600,
)
```

**Fallback Strategies**:
```python
from agno.rate_limit import FallbackStrategy

# If Redis is unavailable, fall back to local rate limiting
limiter = DistributedRateLimiter(
    rate_limit_id="resilient_api",
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.TOKEN_BUCKET,
    fallback_strategy=FallbackStrategy.LOCAL_ONLY,  # or ALLOW_ALL, DENY_ALL
    capacity=100,
    refill_rate=100/60,
)
```

**Distributed Stats**:
```python
stats = limiter.get_distributed_stats()
print(f"Distributed state: {stats}")
```

---

## Usage Examples

### Example 1: Rate Limiting Model API Calls

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.rate_limit import TokenBucketRateLimiter
from agno.exceptions import ModelRateLimitError

# Create rate limiter for OpenAI API
rate_limiter = TokenBucketRateLimiter(
    rate_limit_id="openai_gpt4",
    capacity=100,
    refill_rate=100/60,  # 100 requests per minute
    raise_on_limit=False,
)

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    description="Rate-limited agent",
)

def run_agent_with_rate_limiting(message: str):
    """Run agent with rate limiting"""
    if not rate_limiter.allow_request():
        retry_after = rate_limiter.get_retry_after()
        raise ModelRateLimitError(
            f"Rate limit exceeded, retry after {retry_after:.2f}s",
            model_name="gpt-4",
        )

    return agent.run(message)

# Usage
try:
    response = run_agent_with_rate_limiting("Hello!")
    print(response.content)
except ModelRateLimitError as e:
    print(f"Rate limited: {e}")
```

### Example 2: Per-User Rate Limiting

```python
from typing import Dict
from agno.rate_limit import SlidingWindowRateLimiter

class UserRateLimiter:
    """Manage per-user rate limits"""

    def __init__(self, max_requests: int = 100, window_size: float = 3600):
        self.max_requests = max_requests
        self.window_size = window_size
        self.limiters: Dict[str, SlidingWindowRateLimiter] = {}

    def allow_request(self, user_id: str) -> bool:
        """Check if user can make request"""
        if user_id not in self.limiters:
            self.limiters[user_id] = SlidingWindowRateLimiter(
                rate_limit_id=user_id,
                max_requests=self.max_requests,
                window_size=self.window_size,
            )

        return self.limiters[user_id].allow_request()

    def get_user_stats(self, user_id: str) -> dict:
        """Get user's rate limit stats"""
        if user_id not in self.limiters:
            return {"requests": 0, "limit": self.max_requests}

        limiter = self.limiters[user_id]
        return {
            "requests": limiter.get_current_count(),
            "limit": self.max_requests,
            "retry_after": limiter.get_retry_after(),
        }

# Usage
user_limiter = UserRateLimiter(max_requests=100, window_size=3600)

def handle_api_request(user_id: str, request_data: dict):
    if not user_limiter.allow_request(user_id):
        stats = user_limiter.get_user_stats(user_id)
        return {
            "error": "Rate limit exceeded",
            "retry_after": stats["retry_after"],
        }

    # Process request
    return {"success": True}
```

### Example 3: Workflow with Rate Limiting

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.rate_limit import TokenBucketRateLimiter
from agno.run.response import RunResponse

class RateLimitedWorkflow(Workflow):
    """Workflow with built-in rate limiting"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Rate limiter for external API calls
        self.api_limiter = TokenBucketRateLimiter(
            rate_limit_id="workflow_api",
            capacity=50,
            refill_rate=50/60,
        )

        # Rate limiter for model calls
        self.model_limiter = TokenBucketRateLimiter(
            rate_limit_id="workflow_model",
            capacity=100,
            refill_rate=100/60,
        )

    def run(self, task: str) -> RunResponse:
        """Run workflow with rate limiting"""

        # Check model rate limit
        if not self.model_limiter.allow_request():
            retry_after = self.model_limiter.get_retry_after()
            return RunResponse(
                content=f"Model rate limit exceeded, retry after {retry_after:.2f}s",
                event="run_error",
            )

        # Execute workflow logic
        result = self.execute_task(task)

        return RunResponse(content=result)

    def call_external_api(self):
        """Call external API with rate limiting"""
        if not self.api_limiter.allow_request():
            retry_after = self.api_limiter.get_retry_after()
            raise Exception(f"API rate limited, retry after {retry_after:.2f}s")

        # Make API call
        pass
```

### Example 4: Distributed Multi-Tenant Rate Limiting

```python
import redis
from agno.rate_limit import DistributedRateLimiter, DistributedAlgorithm

class TenantRateLimiter:
    """Distributed rate limiting for multi-tenant application"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

        # Different tiers with different limits
        self.tiers = {
            "free": {"max_requests": 100, "window_size": 3600},
            "pro": {"max_requests": 1000, "window_size": 3600},
            "enterprise": {"max_requests": 10000, "window_size": 3600},
        }

    def get_limiter(self, tenant_id: str, tier: str) -> DistributedRateLimiter:
        """Get rate limiter for tenant"""
        limits = self.tiers.get(tier, self.tiers["free"])

        return DistributedRateLimiter(
            rate_limit_id=f"tenant:{tenant_id}",
            redis_client=self.redis_client,
            algorithm=DistributedAlgorithm.SLIDING_WINDOW,
            max_requests=limits["max_requests"],
            window_size=limits["window_size"],
        )

    def allow_request(self, tenant_id: str, tier: str) -> bool:
        """Check if tenant can make request"""
        limiter = self.get_limiter(tenant_id, tier)
        return limiter.allow_request()

# Usage
redis_client = redis.Redis(host='localhost', port=6379)
tenant_limiter = TenantRateLimiter(redis_client)

def handle_tenant_request(tenant_id: str, tier: str, request_data: dict):
    if not tenant_limiter.allow_request(tenant_id, tier):
        return {"error": "Rate limit exceeded for your tier"}

    # Process request
    return {"success": True}
```

---

## FSA State Diagrams

### Token Bucket FSA

```
┌─────────────┐
│  AVAILABLE  │ (tokens > 80% capacity)
└──────┬──────┘
       │ consume tokens (tokens < 80%)
       ↓
┌─────────────┐
│   WARNING   │ (20% < tokens < 80%)
└──────┬──────┘
       │ consume tokens (tokens < 20%)
       ↓
┌─────────────┐
│ RECOVERING  │ (0% < tokens < 20%, refilling)
└──────┬──────┘
       │ consume tokens (tokens = 0)
       ↓
┌─────────────┐
│   LIMITED   │ (tokens = 0)
└──────┬──────┘
       │ refill over time
       ↓
     (back to AVAILABLE)
```

### Sliding/Fixed Window FSA

```
┌─────────────┐
│  AVAILABLE  │ (count < 80% of max)
└──────┬──────┘
       │ increment count
       ↓
┌─────────────┐
│   WARNING   │ (80% < count < 100%)
└──────┬──────┘
       │ increment count
       ↓
┌─────────────┐
│   LIMITED   │ (count >= max)
└──────┬──────┘
       │ requests expire / window resets
       ↓
┌─────────────┐
│ RECOVERING  │ (requests expiring)
└──────┬──────┘
       │
       ↓
     (back to AVAILABLE)
```

---

## Integration Patterns

### Pattern 1: Agent Pre-Hook Integration

```python
from agno.agent import Agent
from agno.tools import Function
from agno.rate_limit import TokenBucketRateLimiter

# Create rate limiter
limiter = TokenBucketRateLimiter(
    rate_limit_id="tool_api",
    capacity=50,
    refill_rate=50/60,
)

def rate_limited_hook(function_call):
    """Pre-hook that enforces rate limiting"""
    if not limiter.allow_request():
        retry_after = limiter.get_retry_after()
        raise Exception(f"Rate limited, retry after {retry_after:.2f}s")

# Add hook to tool
def call_external_api(query: str) -> str:
    """Call external API"""
    # API call logic
    return "result"

api_tool = Function.from_callable(call_external_api)
api_tool.pre_hook = rate_limited_hook

agent = Agent(
    tools=[api_tool],
    description="Agent with rate-limited tools",
)
```

### Pattern 2: Workflow Storage Integration

```python
from agno.workflow import Workflow
from agno.storage.postgres import PgStorage
from agno.rate_limit import FixedWindowRateLimiter

class MeteredWorkflow(Workflow):
    """Workflow that tracks and limits usage"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.rate_limiter = FixedWindowRateLimiter(
            rate_limit_id=f"workflow:{self.workflow_id}",
            max_requests=1000,
            window_size=86400,  # Daily limit
        )

    def run(self, **kwargs):
        # Check rate limit
        if not self.rate_limiter.allow_request():
            time_until_reset = self.rate_limiter.get_time_until_reset()
            return RunResponse(
                content=f"Daily limit reached, resets in {time_until_reset/3600:.1f} hours"
            )

        # Store metrics in session_state
        self.session_state["rate_limit_metrics"] = self.rate_limiter.get_metrics()

        # Execute workflow
        return super().run(**kwargs)
```

### Pattern 3: Exception Handling Integration

```python
from agno.exceptions import AgentRunException, RetryAgentRun
from agno.rate_limit import RateLimitExceeded
import time

def execute_with_rate_limit_retry(limiter, func, max_retries=3):
    """Execute function with automatic retry on rate limit"""

    for attempt in range(max_retries):
        try:
            if limiter.allow_request():
                return func()
            else:
                raise RateLimitExceeded(
                    message="Rate limit exceeded",
                    retry_after=limiter.get_retry_after(),
                )

        except RateLimitExceeded as e:
            if attempt < max_retries - 1:
                print(f"Rate limited, waiting {e.retry_after:.2f}s...")
                time.sleep(e.retry_after)
            else:
                raise RetryAgentRun(
                    exc=e,
                    agent_message=f"Rate limit exceeded after {max_retries} retries",
                )

    raise Exception("Max retries exceeded")
```

---

## Performance Considerations

### Token Bucket
- **Memory**: O(1) - stores only current tokens and timestamp
- **Time Complexity**: O(1) per request
- **Best For**: Single-instance deployments, burst handling

### Sliding Window
- **Memory**: O(N) where N = number of requests in window
- **Time Complexity**: O(log N) for adding/removing requests
- **Best For**: Accurate rate limiting, moderate traffic

### Fixed Window
- **Memory**: O(1) - stores only counter and window start
- **Time Complexity**: O(1) per request
- **Best For**: High-traffic scenarios, billing periods

### Distributed (Redis)
- **Memory**: Depends on algorithm (stored in Redis)
- **Time Complexity**: O(1) for token bucket/fixed window, O(log N) for sliding window
- **Network**: Requires Redis connection (adds latency ~1-5ms)
- **Best For**: Multi-server deployments, global limits

---

## Best Practices

### 1. Choose the Right Algorithm

- **Token Bucket**: API rate limiting, burst handling
- **Sliding Window**: User-facing limits, precise enforcement
- **Fixed Window**: Simple limits, billing periods
- **Distributed**: Multi-server, microservices

### 2. Set Appropriate Capacities

```python
# Conservative approach - match provider limits
openai_limiter = TokenBucketRateLimiter(
    rate_limit_id="openai",
    capacity=90,         # 90% of actual limit (100)
    refill_rate=90/60,   # Leave 10% buffer
)
```

### 3. Handle Rate Limits Gracefully

```python
if not limiter.allow_request():
    retry_after = limiter.get_retry_after()

    # Option 1: Return error to user
    return {"error": f"Rate limited, retry after {retry_after:.2f}s"}

    # Option 2: Queue request for later
    task_queue.enqueue(request, delay=retry_after)

    # Option 3: Use exponential backoff
    time.sleep(retry_after)
    return retry_request()
```

### 4. Monitor Metrics

```python
# Log metrics periodically
metrics = limiter.get_metrics()
logger.info(f"Rate limiter metrics: {metrics}")

# Alert on high utilization
if metrics["utilization"] > 0.9:
    alert("Rate limiter at 90% capacity")

# Track denial rate
if metrics["denial_rate"] > 0.1:
    alert("10% of requests are being rate limited")
```

### 5. Use Distributed Limiters for Multi-Server

```python
# ❌ Don't use local limiters in multi-server setup
# Each server will have its own limit (3x the intended limit!)
local_limiter = TokenBucketRateLimiter(...)

# ✅ Use distributed limiter
distributed_limiter = DistributedRateLimiter(
    redis_client=redis_client,
    algorithm=DistributedAlgorithm.TOKEN_BUCKET,
    ...
)
```

### 6. Implement Fallback Strategies

```python
# Always have a fallback when using distributed limiters
limiter = DistributedRateLimiter(
    redis_client=redis_client,
    fallback_strategy=FallbackStrategy.LOCAL_ONLY,  # Graceful degradation
    ...
)
```

### 7. Test Rate Limiting

```python
def test_rate_limiter():
    limiter = TokenBucketRateLimiter(
        rate_limit_id="test",
        capacity=10,
        refill_rate=10,
    )

    # Should allow first 10 requests
    for i in range(10):
        assert limiter.allow_request() == True

    # 11th request should be denied
    assert limiter.allow_request() == False

    # Wait for refill
    time.sleep(1)
    assert limiter.allow_request() == True
```

---

## Conclusion

The Agno Framework now provides comprehensive, production-ready rate limiting FSA patterns that:

1. ✅ Support multiple algorithms (token bucket, sliding window, fixed window)
2. ✅ Work in both single-server and distributed environments
3. ✅ Provide detailed metrics and observability
4. ✅ Integrate seamlessly with existing Agent and Workflow patterns
5. ✅ Follow FSA design principles with clear state transitions
6. ✅ Include graceful error handling and fallback strategies

---

## References

- Base Rate Limiter: `libs/agno/agno/rate_limit/base.py`
- Token Bucket: `libs/agno/agno/rate_limit/token_bucket.py`
- Sliding Window: `libs/agno/agno/rate_limit/sliding_window.py`
- Fixed Window: `libs/agno/agno/rate_limit/fixed_window.py`
- Distributed: `libs/agno/agno/rate_limit/distributed.py`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-19
**Status**: Complete

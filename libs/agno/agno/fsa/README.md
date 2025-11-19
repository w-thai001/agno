# Agno FSA (Functional Specification Agent)

High-velocity, credit-conscious functional components for Core Infrastructure.

## Overview

FSA (Functional Specification Agent) is a design pattern for creating specialized, self-contained functional components that are:

- **High-velocity**: Optimized for fast operations with minimal overhead
- **Credit-conscious**: Designed to minimize resource consumption
- **Well-specified**: Clear inputs, outputs, and logic
- **Self-documenting**: Comprehensive examples and tests

## Cache Manager FSA

The Cache Manager FSA provides in-memory caching with LRU eviction, TTL expiration, and size management.

### Features

- **LRU Eviction**: Least Recently Used eviction policy
- **TTL Expiration**: Time-To-Live based automatic expiration
- **Size Management**: Maximum cache size enforcement
- **Thread-Safe**: Safe for concurrent access
- **Auto Cleanup**: Background thread for expired entry cleanup
- **Comprehensive Stats**: Detailed performance metrics
- **Eviction Reporting**: Track why entries were evicted

### Quick Start

```python
from agno.fsa import CacheManagerFSA

# Create cache instance
cache = CacheManagerFSA(
    max_cache_size=1000,
    default_ttl_seconds=300,
    enable_auto_cleanup=True,
)

# Set values
cache.set("user:1001", {"name": "Alice", "role": "admin"}, ttl_seconds=300)

# Get values
value, hit = cache.get("user:1001")
print(f"Value: {value}, Cache Hit: {hit}")

# Get statistics
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.2%}")

# Cleanup
cache.shutdown()
```

### Inputs

- **cache_key** (str): Unique identifier for cached data
- **cache_value** (Any): Data to cache (can be any Python object)
- **ttl_seconds** (Optional[int]): Time-to-live in seconds
- **max_cache_size** (int): Maximum number of cache entries

### Outputs

- **cached_data** (Any): Retrieved cached data
- **cache_stats** (Dict): Performance metrics including hits, misses, evictions
- **eviction_report** (Dict): Detailed eviction activity report

### Logic

1. **LRU Eviction**: When cache reaches max size, least recently used entry is evicted
2. **TTL Expiration**: Entries automatically expire after TTL seconds
3. **Size Management**: Cache never exceeds max_cache_size entries
4. **Auto Cleanup**: Background thread periodically removes expired entries

### Examples

#### Example 1: Basic Operations

```python
from agno.fsa import CacheManagerFSA

cache = CacheManagerFSA(max_cache_size=5)

# Set values
cache.set("user:1001", {"name": "Alice", "role": "admin"})
cache.set("config:api_key", "sk-abc123xyz", ttl_seconds=3600)

# Get values
value, hit = cache.get("user:1001")

# Delete
cache.delete("user:1001")

cache.shutdown()
```

#### Example 2: LRU Eviction

```python
from agno.fsa import CacheManagerFSA

cache = CacheManagerFSA(max_cache_size=3)

# Fill beyond capacity - triggers LRU eviction
for i in range(5):
    cache.set(f"key:{i}", f"value:{i}")

# Check eviction report
report = cache.get_eviction_report()
print(f"Total evictions: {report['total_evictions']}")

cache.shutdown()
```

#### Example 3: TTL Expiration

```python
from agno.fsa import CacheManagerFSA
import time

cache = CacheManagerFSA(default_ttl_seconds=2)

# Set with TTL
cache.set("temp:session", "session_data", ttl_seconds=1)

# Immediate get succeeds
value, hit = cache.get("temp:session")
print(f"Immediate: {hit}")  # True

# Wait for expiration
time.sleep(2)

# Get fails after expiration
value, hit = cache.get("temp:session")
print(f"After expiration: {hit}")  # False

cache.shutdown()
```

#### Example 4: Statistics

```python
from agno.fsa import CacheManagerFSA

cache = CacheManagerFSA(max_cache_size=10)

# Perform operations
cache.set("key:1", "value:1")
cache.get("key:1")  # Hit
cache.get("key:999")  # Miss

# Get detailed stats
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.2%}")
print(f"Utilization: {stats['utilization_rate']:.2%}")

cache.shutdown()
```

### Context Manager

```python
from agno.fsa import CacheManagerFSA

with CacheManagerFSA(max_cache_size=100) as cache:
    cache.set("key", "value")
    value, hit = cache.get("key")
    # Automatic cleanup on exit
```

### API Reference

#### CacheManagerFSA

**Constructor**

```python
CacheManagerFSA(
    max_cache_size: int = 1000,
    default_ttl_seconds: Optional[int] = None,
    cleanup_interval_seconds: int = 60,
    enable_auto_cleanup: bool = True,
)
```

**Methods**

- `set(cache_key, cache_value, ttl_seconds=None) -> bool`: Set a cache entry
- `get(cache_key) -> Tuple[Optional[Any], bool]`: Get a cache entry
- `delete(cache_key) -> bool`: Delete a cache entry
- `clear() -> int`: Clear all cache entries
- `get_stats() -> Dict[str, Any]`: Get cache statistics
- `get_eviction_report() -> Dict[str, Any]`: Get eviction report
- `get_entry_info(cache_key) -> Optional[Dict[str, Any]]`: Get entry details
- `cleanup_expired() -> int`: Manually cleanup expired entries
- `shutdown()`: Shutdown cache and cleanup resources

### Thread Safety

All operations are thread-safe using internal locking. The cache can be safely accessed from multiple threads.

### Performance Considerations

- **Get/Set Operations**: O(1) average time complexity
- **LRU Eviction**: O(1) time complexity
- **TTL Checking**: O(1) per entry
- **Auto Cleanup**: Runs in background thread

### Testing

Run the included tests:

```bash
python -m unittest libs/agno/tests/unit/fsa/test_cache_manager.py
```

Or run the examples:

```bash
python libs/agno/agno/fsa/cache_manager.py
```

## Future FSA Components

The FSA pattern will be extended to other Core Infrastructure components:

- **Rate Limiter FSA**: Token bucket and sliding window rate limiting
- **Circuit Breaker FSA**: Fault tolerance and failure handling
- **Connection Pool FSA**: Database and HTTP connection pooling
- **Message Queue FSA**: In-memory message queuing

## Contributing

When creating new FSA components, follow this structure:

1. **Clear Specification**: Define inputs, outputs, and logic
2. **Self-Contained**: Single file implementation when possible
3. **Examples**: Include comprehensive usage examples
4. **Tests**: Full test coverage for all functionality
5. **Documentation**: Clear README with API reference

## License

Part of the Agno framework. See main repository for license information.

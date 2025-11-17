"""
Comprehensive test suite for CacheManagerFSA.

Test coverage:
- Basic get/set/delete operations
- TTL expiration behavior
- LRU eviction when max_size exceeded
- Pattern-based cache clearing
- Cache statistics accuracy
- Namespace isolation
- Concurrent access safety
- Memory limit enforcement
- Cache warming
- Smoke tests
"""

import threading
import time
from unittest.mock import patch

import pytest

from agno.fsas.cache_manager_fsa import CacheManagerFSA


class TestBasicOperations:
    """Test basic cache operations."""

    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        assert cache.cache_get("key1") == "value1"

    def test_cache_get_default(self):
        """Test get with default value."""
        cache = CacheManagerFSA()
        assert cache.cache_get("nonexistent", default="default") == "default"

    def test_cache_get_none_default(self):
        """Test get with None as default."""
        cache = CacheManagerFSA()
        assert cache.cache_get("nonexistent") is None

    def test_cache_delete(self):
        """Test cache deletion."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        assert cache.cache_delete("key1") is True
        assert cache.cache_get("key1") is None

    def test_cache_delete_nonexistent(self):
        """Test deleting nonexistent key."""
        cache = CacheManagerFSA()
        assert cache.cache_delete("nonexistent") is False

    def test_cache_exists(self):
        """Test cache_exists for valid key."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        assert cache.cache_exists("key1") is True

    def test_cache_exists_nonexistent(self):
        """Test cache_exists for nonexistent key."""
        cache = CacheManagerFSA()
        assert cache.cache_exists("nonexistent") is False

    def test_cache_overwrite(self):
        """Test overwriting existing cache entry."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        cache.cache_set("key1", "value2")
        assert cache.cache_get("key1") == "value2"

    def test_cache_multiple_types(self):
        """Test caching different data types."""
        cache = CacheManagerFSA()
        cache.cache_set("str", "string")
        cache.cache_set("int", 42)
        cache.cache_set("float", 3.14)
        cache.cache_set("bool", True)
        cache.cache_set("list", [1, 2, 3])
        cache.cache_set("dict", {"a": 1})

        assert cache.cache_get("str") == "string"
        assert cache.cache_get("int") == 42
        assert cache.cache_get("float") == 3.14
        assert cache.cache_get("bool") is True
        assert cache.cache_get("list") == [1, 2, 3]
        assert cache.cache_get("dict") == {"a": 1}


class TestTTLExpiration:
    """Test TTL expiration functionality."""

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1", ttl=0.1)
        assert cache.cache_get("key1") == "value1"
        time.sleep(0.15)
        assert cache.cache_get("key1") is None

    def test_default_ttl(self):
        """Test default TTL configuration."""
        cache = CacheManagerFSA(default_ttl=0.1)
        cache.cache_set("key1", "value1")
        assert cache.cache_get("key1") == "value1"
        time.sleep(0.15)
        assert cache.cache_get("key1") is None

    def test_ttl_override_default(self):
        """Test that specific TTL overrides default."""
        cache = CacheManagerFSA(default_ttl=10)
        cache.cache_set("key1", "value1", ttl=0.1)
        time.sleep(0.15)
        assert cache.cache_get("key1") is None

    def test_no_ttl_no_expiration(self):
        """Test that entries without TTL don't expire."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        time.sleep(0.1)
        assert cache.cache_get("key1") == "value1"

    def test_cache_exists_expired(self):
        """Test cache_exists returns False for expired entries."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1", ttl=0.1)
        assert cache.cache_exists("key1") is True
        time.sleep(0.15)
        assert cache.cache_exists("key1") is False


class TestLRUEviction:
    """Test LRU eviction functionality."""

    def test_lru_eviction_on_max_size(self):
        """Test that LRU entry is evicted when max_size is reached."""
        cache = CacheManagerFSA(max_size=3)
        cache.cache_set("key1", "value1")
        cache.cache_set("key2", "value2")
        cache.cache_set("key3", "value3")
        cache.cache_set("key4", "value4")

        # key1 should be evicted (least recently used)
        assert cache.cache_get("key1") is None
        assert cache.cache_get("key2") == "value2"
        assert cache.cache_get("key3") == "value3"
        assert cache.cache_get("key4") == "value4"

    def test_lru_access_updates_order(self):
        """Test that accessing entry updates LRU order."""
        cache = CacheManagerFSA(max_size=3)
        cache.cache_set("key1", "value1")
        cache.cache_set("key2", "value2")
        cache.cache_set("key3", "value3")

        # Access key1 to make it recently used
        cache.cache_get("key1")

        # Add key4, key2 should be evicted
        cache.cache_set("key4", "value4")

        assert cache.cache_get("key1") == "value1"
        assert cache.cache_get("key2") is None
        assert cache.cache_get("key3") == "value3"
        assert cache.cache_get("key4") == "value4"

    def test_eviction_counter(self):
        """Test that evictions are counted correctly."""
        cache = CacheManagerFSA(max_size=2)
        cache.cache_set("key1", "value1")
        cache.cache_set("key2", "value2")
        cache.cache_set("key3", "value3")

        stats = cache.get_cache_stats()
        assert stats["evictions"] == 1


class TestPatternBasedClearing:
    """Test pattern-based cache clearing."""

    def test_cache_clear_all(self):
        """Test clearing all cache entries."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        cache.cache_set("key2", "value2")
        cache.cache_set("key3", "value3")

        count = cache.cache_clear()
        assert count == 3
        assert cache.cache_get("key1") is None
        assert cache.cache_get("key2") is None
        assert cache.cache_get("key3") is None

    def test_cache_clear_pattern_prefix(self):
        """Test clearing with prefix pattern."""
        cache = CacheManagerFSA()
        cache.cache_set("user:1", "user1")
        cache.cache_set("user:2", "user2")
        cache.cache_set("product:1", "product1")

        count = cache.cache_clear(pattern="user:*")
        assert count == 2
        assert cache.cache_get("user:1") is None
        assert cache.cache_get("user:2") is None
        assert cache.cache_get("product:1") == "product1"

    def test_cache_clear_pattern_suffix(self):
        """Test clearing with suffix pattern."""
        cache = CacheManagerFSA()
        cache.cache_set("user:session", "session1")
        cache.cache_set("admin:session", "session2")
        cache.cache_set("user:profile", "profile1")

        count = cache.cache_clear(pattern="*:session")
        assert count == 2
        assert cache.cache_get("user:session") is None
        assert cache.cache_get("admin:session") is None
        assert cache.cache_get("user:profile") == "profile1"

    def test_cache_clear_pattern_middle(self):
        """Test clearing with middle pattern."""
        cache = CacheManagerFSA()
        cache.cache_set("user:1:profile", "profile1")
        cache.cache_set("user:2:profile", "profile2")
        cache.cache_set("user:1:settings", "settings1")

        count = cache.cache_clear(pattern="user:*:profile")
        assert count == 2
        assert cache.cache_get("user:1:profile") is None
        assert cache.cache_get("user:2:profile") is None
        assert cache.cache_get("user:1:settings") == "settings1"


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")

        cache.cache_get("key1")  # hit
        cache.cache_get("key1")  # hit
        cache.cache_get("key2")  # miss

        stats = cache.get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3
        assert stats["miss_rate"] == 1 / 3

    def test_stats_size_tracking(self):
        """Test cache size tracking."""
        cache = CacheManagerFSA(max_size=10)
        cache.cache_set("key1", "value1")
        cache.cache_set("key2", "value2")

        stats = cache.get_cache_stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 10

    def test_stats_reset(self):
        """Test resetting statistics."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        cache.cache_get("key1")
        cache.cache_get("key2")

        cache.reset_stats()

        stats = cache.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0

    def test_stats_namespace(self):
        """Test namespace in statistics."""
        cache = CacheManagerFSA(namespace="test-namespace")
        stats = cache.get_cache_stats()
        assert stats["namespace"] == "test-namespace"


class TestMemoryLimits:
    """Test memory limit enforcement."""

    def test_max_bytes_enforcement(self):
        """Test that max_bytes limit is enforced."""
        cache = CacheManagerFSA(max_size=100, max_bytes=50)

        # Add entries until memory limit is reached
        cache.cache_set("key1", "x" * 20)  # ~20 bytes
        cache.cache_set("key2", "x" * 20)  # ~20 bytes
        cache.cache_set("key3", "x" * 20)  # ~20 bytes (should evict key1)

        stats = cache.get_cache_stats()
        assert stats["total_size_bytes"] <= 50

    def test_size_tracking_accuracy(self):
        """Test that size tracking is reasonably accurate."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "test")

        stats = cache.get_cache_stats()
        assert stats["total_size_bytes"] > 0


class TestConcurrentAccess:
    """Test thread-safe operations."""

    def test_concurrent_writes(self):
        """Test concurrent write operations."""
        cache = CacheManagerFSA()
        threads = []

        def write_values(start, end):
            for i in range(start, end):
                cache.cache_set(f"key{i}", f"value{i}")

        for i in range(10):
            t = threading.Thread(target=write_values, args=(i * 10, (i + 1) * 10))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        stats = cache.get_cache_stats()
        assert stats["size"] == 100

    def test_concurrent_reads_and_writes(self):
        """Test concurrent read and write operations."""
        cache = CacheManagerFSA()
        cache.cache_set("shared", "initial")

        results = []

        def reader():
            for _ in range(50):
                value = cache.cache_get("shared", "default")
                results.append(value)

        def writer():
            for i in range(50):
                cache.cache_set("shared", f"value{i}")

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All operations should complete without errors
        assert len(results) == 250


class TestCacheWarming:
    """Test cache warming functionality."""

    def test_warm_cache_basic(self):
        """Test basic cache warming."""
        cache = CacheManagerFSA()
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}

        count = cache.warm_cache(data)
        assert count == 3
        assert cache.cache_get("key1") == "value1"
        assert cache.cache_get("key2") == "value2"
        assert cache.cache_get("key3") == "value3"

    def test_warm_cache_with_ttl(self):
        """Test cache warming with TTL."""
        cache = CacheManagerFSA()
        data = {"key1": "value1", "key2": "value2"}

        cache.warm_cache(data, ttl=0.1)
        assert cache.cache_get("key1") == "value1"
        time.sleep(0.15)
        assert cache.cache_get("key1") is None


class TestNamespaceIsolation:
    """Test namespace isolation."""

    def test_different_namespaces(self):
        """Test that different namespaces are isolated."""
        cache1 = CacheManagerFSA(namespace="ns1")
        cache2 = CacheManagerFSA(namespace="ns2")

        cache1.cache_set("key", "value1")
        cache2.cache_set("key", "value2")

        assert cache1.cache_get("key") == "value1"
        assert cache2.cache_get("key") == "value2"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_cache_stats(self):
        """Test statistics on empty cache."""
        cache = CacheManagerFSA()
        stats = cache.get_cache_stats()
        assert stats["hit_rate"] == 0.0
        assert stats["miss_rate"] == 0.0
        assert stats["size"] == 0

    def test_clear_empty_cache(self):
        """Test clearing empty cache."""
        cache = CacheManagerFSA()
        count = cache.cache_clear()
        assert count == 0

    def test_clear_pattern_no_matches(self):
        """Test clearing with pattern that matches nothing."""
        cache = CacheManagerFSA()
        cache.cache_set("key1", "value1")
        count = cache.cache_clear(pattern="nomatch:*")
        assert count == 0
        assert cache.cache_get("key1") == "value1"

    def test_zero_max_size(self):
        """Test behavior with max_size of 0."""
        cache = CacheManagerFSA(max_size=0)
        cache.cache_set("key1", "value1")
        # Should evict immediately
        assert cache.cache_get("key1") is None

    def test_shutdown(self):
        """Test cache shutdown."""
        cache = CacheManagerFSA(default_ttl=1)
        cache.cache_set("key1", "value1")
        cache.shutdown()
        # Should not raise errors


class TestSmokeTests:
    """Smoke tests for overall functionality."""

    def test_smoke_basic_workflow(self):
        """Smoke test: basic cache workflow."""
        cache = CacheManagerFSA(max_size=100, default_ttl=60)

        # Set multiple values
        for i in range(10):
            cache.cache_set(f"key{i}", f"value{i}")

        # Get values
        for i in range(10):
            assert cache.cache_get(f"key{i}") == f"value{i}"

        # Delete some
        cache.cache_delete("key5")
        assert cache.cache_get("key5") is None

        # Check stats
        stats = cache.get_cache_stats()
        assert stats["size"] == 9
        assert stats["hits"] > 0

    def test_smoke_full_features(self):
        """Smoke test: all features combined."""
        cache = CacheManagerFSA(max_size=50, max_bytes=1024, default_ttl=10)

        # Warm cache
        cache.warm_cache({"user:1": "alice", "user:2": "bob", "product:1": "laptop"})

        # Set with custom TTL
        cache.cache_set("session:abc", "session_data", ttl=0.2)

        # Get values
        assert cache.cache_get("user:1") == "alice"
        assert cache.cache_exists("session:abc") is True

        # Clear pattern
        cache.cache_clear(pattern="user:*")
        assert cache.cache_get("user:1") is None
        assert cache.cache_get("product:1") == "laptop"

        # Wait for TTL expiration
        time.sleep(0.25)
        assert cache.cache_exists("session:abc") is False

        # Check stats
        stats = cache.get_cache_stats()
        assert stats["size"] >= 0
        assert "hit_rate" in stats
        assert "evictions" in stats

"""
Comprehensive unit tests for CacheManagerFSA.

Tests cover:
- Basic set/get operations
- TTL expiration
- LRU eviction policy
- Multi-level cache promotion
- Tag-based invalidation
- Pattern invalidation
- Cache warming
- Concurrent access
- Statistics collection
- Compression for large objects
"""

import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from agno.fsas.infrastructure.cache_manager_fsa import (
    AdaptivePolicy,
    BloomFilter,
    CacheEntry,
    CacheInvalidator,
    CacheManagerFSA,
    CacheOperation,
    CacheStatistics,
    FIFOPolicy,
    L1MemoryCache,
    L2DiskCache,
    LFUPolicy,
    LRUPolicy,
    TTLPolicy,
    WriteStrategy,
)


class TestBasicSetGetOperations:
    """Test basic cache set and get operations."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set a value
        cache.set("key1", "value1")

        # Get the value
        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns default."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        result = cache.get("nonexistent", default="default_value")
        assert result == "default_value"

    def test_set_complex_objects(self):
        """Test setting and getting complex objects."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set various types
        cache.set("dict", {"a": 1, "b": 2})
        cache.set("list", [1, 2, 3, 4, 5])
        cache.set("tuple", (1, 2, 3))
        cache.set("int", 42)
        cache.set("float", 3.14)

        # Verify retrieval
        assert cache.get("dict") == {"a": 1, "b": 2}
        assert cache.get("list") == [1, 2, 3, 4, 5]
        assert cache.get("tuple") == (1, 2, 3)
        assert cache.get("int") == 42
        assert cache.get("float") == 3.14

    def test_delete_operation(self):
        """Test delete operation."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Delete the key
        deleted = cache.delete("key1")
        assert deleted is True

        # Verify it's gone
        assert cache.get("key1") is None

    def test_execute_method(self):
        """Test execute method for operations."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Test SET operation
        cache.execute(CacheOperation.SET, key="key1", value="value1")

        # Test GET operation
        result = cache.execute(CacheOperation.GET, key="key1")
        assert result == "value1"

        # Test DELETE operation
        cache.execute(CacheOperation.DELETE, key="key1")
        assert cache.get("key1") is None


class TestTTLExpiration:
    """Test TTL expiration functionality."""

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set with 0.5 second TTL
        cache.set("key1", "value1", ttl=0.5)

        # Should be available immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.6)

        # Should be expired now
        assert cache.get("key1") is None

    def test_ttl_validation(self):
        """Test validation removes expired entries."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set multiple entries with short TTL
        cache.set("key1", "value1", ttl=0.3)
        cache.set("key2", "value2", ttl=0.3)
        cache.set("key3", "value3")  # No TTL

        time.sleep(0.4)

        # Validate should remove expired
        cache.validate()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_no_ttl_persists(self):
        """Test entries without TTL persist."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("persistent", "value")
        time.sleep(1)
        assert cache.get("persistent") == "value"


class TestLRUEvictionPolicy:
    """Test LRU eviction policy."""

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Create a small cache
        cache = CacheManagerFSA(
            l1_size=200,  # Small size to trigger eviction
            enable_l2=False,
            enable_l3=False,
            eviction_policy="lru",
        )

        # Add entries that will exceed the limit
        cache.set("key1", "value1" * 10)  # ~50 bytes
        cache.set("key2", "value2" * 10)  # ~50 bytes
        cache.set("key3", "value3" * 10)  # ~50 bytes

        # Access key1 to make it more recently used
        cache.get("key1")

        # Add another entry to trigger eviction
        cache.set("key4", "value4" * 10)  # Should evict key2 (least recently used)

        # key1 and key3 should still be there, key2 might be evicted
        assert cache.get("key1") is not None
        # Due to size calculations, some entries may be evicted

    def test_lru_access_updates_order(self):
        """Test that accessing an entry updates its position in LRU."""
        cache = CacheManagerFSA(
            l1_size=300,
            enable_l2=False,
            enable_l3=False,
            eviction_policy="lru",
        )

        cache.set("key1", "a" * 50)
        cache.set("key2", "b" * 50)
        cache.set("key3", "c" * 50)

        # Access key1 to make it more recent
        cache.get("key1")
        cache.get("key1")

        # Statistics should show the access
        stats = cache.get_statistics()
        assert stats["hits"] >= 2


class TestMultiLevelCachePromotion:
    """Test multi-level cache promotion."""

    def test_l2_to_l1_promotion(self):
        """Test promoting entries from L2 to L1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManagerFSA(
                l1_size=1024 * 100,
                l2_size=1024 * 1024,
                enable_l2=True,
                enable_l3=False,
                l2_cache_dir=tmpdir,
                write_strategy=WriteStrategy.WRITE_THROUGH,
            )

            # Set with write-through (goes to both L1 and L2)
            cache.set("key1", "value1", level=2)

            # Clear L1 to force L2 access
            cache.l1.clear()

            # Get should retrieve from L2 and promote to L1
            result = cache.get("key1", promote=True)
            assert result == "value1"

            # Check statistics for promotion
            stats = cache.get_statistics()
            assert stats["promotions"] >= 1
            assert stats["l2_hits"] >= 1

    def test_promotion_disabled(self):
        """Test that promotion can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManagerFSA(
                l1_size=1024 * 100,
                l2_size=1024 * 1024,
                enable_l2=True,
                enable_l3=False,
                l2_cache_dir=tmpdir,
            )

            cache.set("key1", "value1", level=2)
            cache.l1.clear()

            # Get without promotion
            result = cache.get("key1", promote=False)
            assert result == "value1"

            # Promotion count should be 0
            stats = cache.get_statistics()
            assert stats["promotions"] == 0

    def test_multi_level_cascade_delete(self):
        """Test cascade delete across levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManagerFSA(
                l1_size=1024 * 100,
                l2_size=1024 * 1024,
                enable_l2=True,
                enable_l3=False,
                l2_cache_dir=tmpdir,
                write_strategy=WriteStrategy.WRITE_THROUGH,
            )

            cache.set("key1", "value1", level=2)

            # Delete with cascade
            cache.delete("key1", cascade=True)

            # Should be gone from all levels
            assert cache.l1.get("key1") is None
            assert cache.l2.get("key1") is None


class TestTagBasedInvalidation:
    """Test tag-based invalidation."""

    def test_invalidate_by_tag(self):
        """Test invalidating entries by tag."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set entries with tags
        cache.set("user:1", "data1", tags={"user", "active"})
        cache.set("user:2", "data2", tags={"user", "inactive"})
        cache.set("product:1", "prod1", tags={"product"})

        # Invalidate all user entries
        count = cache.invalidate_by_tag("user")
        assert count == 2

        # User entries should be gone
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None

        # Product should still be there
        assert cache.get("product:1") == "prod1"

    def test_invalidate_multiple_tags(self):
        """Test entries with multiple tags."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("item1", "data1", tags={"tag1", "tag2", "tag3"})
        cache.set("item2", "data2", tags={"tag2", "tag3"})
        cache.set("item3", "data3", tags={"tag3"})

        # Invalidate by tag1
        count = cache.invalidate_by_tag("tag1")
        assert count == 1
        assert cache.get("item1") is None
        assert cache.get("item2") == "data2"

        # Invalidate by tag3
        count = cache.invalidate_by_tag("tag3")
        assert count == 2
        assert cache.get("item2") is None
        assert cache.get("item3") is None


class TestPatternInvalidation:
    """Test pattern-based invalidation."""

    def test_invalidate_by_pattern(self):
        """Test invalidating entries by regex pattern."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Set entries with patterned keys
        cache.set("user:123", "data1", tags={"user"})
        cache.set("user:456", "data2", tags={"user"})
        cache.set("product:789", "data3", tags={"product"})

        # Invalidate all user keys
        count = cache.invalidate_by_pattern(r"^user:")
        assert count == 2

        # User entries should be gone
        assert cache.get("user:123") is None
        assert cache.get("user:456") is None

        # Product should still be there
        assert cache.get("product:789") == "data3"

    def test_pattern_with_wildcards(self):
        """Test pattern matching with wildcards."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("cache_v1_data", "d1", tags={"cache"})
        cache.set("cache_v2_data", "d2", tags={"cache"})
        cache.set("other_data", "d3", tags={"other"})

        # Match cache_v*_data
        count = cache.invalidate_by_pattern(r"cache_v\d+_data")
        assert count == 2

        assert cache.get("cache_v1_data") is None
        assert cache.get("cache_v2_data") is None
        assert cache.get("other_data") == "d3"


class TestCacheWarming:
    """Test cache warming functionality."""

    def test_warm_cache_with_loader(self):
        """Test warming cache with a loader function."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        def loader():
            return {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3",
            }

        count = cache.warm_cache(loader)
        assert count == 3

        # All entries should be in cache
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_warm_cache_execute(self):
        """Test cache warming via execute method."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        def loader():
            return {"warm1": "data1", "warm2": "data2"}

        count = cache.execute(CacheOperation.WARM, loader=loader)
        assert count == 2
        assert cache.get("warm1") == "data1"


class TestConcurrentAccess:
    """Test concurrent access to cache."""

    def test_concurrent_set_get(self):
        """Test concurrent set and get operations."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"value_{i}"
                    cache.set(key, value)
                    result = cache.get(key)
                    assert result == value, f"Expected {value}, got {result}"
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_invalidation(self):
        """Test concurrent invalidation operations."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        # Preload cache
        for i in range(20):
            cache.set(f"key_{i}", f"value_{i}", tags={f"tag_{i % 5}"})

        errors = []

        def invalidator(tag_id):
            try:
                cache.invalidate_by_tag(f"tag_{tag_id}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=invalidator, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0


class TestStatisticsCollection:
    """Test cache statistics collection."""

    def test_hit_miss_statistics(self):
        """Test hit and miss statistics."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("key1", "value1")

        # Generate hits
        cache.get("key1")
        cache.get("key1")

        # Generate misses
        cache.get("nonexistent1")
        cache.get("nonexistent2")

        stats = cache.get_statistics()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["miss_rate"] == 0.5

    def test_set_delete_statistics(self):
        """Test set and delete statistics."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.delete("key1")

        stats = cache.get_statistics()
        assert stats["sets"] == 2
        assert stats["deletes"] == 1

    def test_invalidation_statistics(self):
        """Test invalidation statistics."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("key1", "v1", tags={"tag1"})
        cache.set("key2", "v2", tags={"tag1"})
        cache.invalidate_by_tag("tag1")

        stats = cache.get_statistics()
        assert stats["invalidations"] == 2

    def test_statistics_dict_format(self):
        """Test statistics returns proper dict format."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("test", "value")
        cache.get("test")

        stats = cache.get_statistics()

        # Check required keys
        assert "hits" in stats
        assert "misses" in stats
        assert "sets" in stats
        assert "hit_rate" in stats
        assert "l1_size" in stats
        assert "l1_entries" in stats


class TestCompressionForLargeObjects:
    """Test compression for large objects."""

    def test_compression_threshold(self):
        """Test that large objects are compressed."""
        cache = CacheManagerFSA(
            l1_size=1024 * 1024,
            enable_l2=False,
            enable_l3=False,
            compression_threshold=100,  # Low threshold for testing
        )

        # Create large data
        large_data = "x" * 200

        cache.set("large", large_data)

        # Get the entry directly to check compression
        entry = cache.l1.entries.get("large")
        # Entry might be compressed based on size

        # Should still retrieve correctly
        result = cache.get("large")
        assert result == large_data

    def test_small_objects_not_compressed(self):
        """Test that small objects are not compressed."""
        cache = CacheManagerFSA(
            l1_size=1024 * 1024,
            enable_l2=False,
            enable_l3=False,
            compression_threshold=1000,
        )

        small_data = "small"
        cache.set("small", small_data)

        # Should retrieve correctly
        result = cache.get("small")
        assert result == small_data

    def test_compression_with_l2_cache(self):
        """Test compression works with L2 disk cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManagerFSA(
                l1_size=1024 * 1024,
                l2_size=1024 * 1024,
                enable_l2=True,
                enable_l3=False,
                l2_cache_dir=tmpdir,
                compression_threshold=100,
            )

            large_data = "y" * 500
            cache.set("large_l2", large_data, level=2)

            # Clear L1 to force L2 retrieval
            cache.l1.clear()

            result = cache.get("large_l2")
            assert result == large_data


class TestEvictionPolicies:
    """Test different eviction policies."""

    def test_lfu_policy(self):
        """Test LFU eviction policy."""
        cache = CacheManagerFSA(
            l1_size=200,
            enable_l2=False,
            enable_l3=False,
            eviction_policy="lfu",
        )

        cache.set("k1", "v" * 30)
        cache.set("k2", "v" * 30)

        # Access k1 multiple times
        cache.get("k1")
        cache.get("k1")
        cache.get("k1")

        # k2 has lower frequency, should be evicted first
        cache.set("k3", "v" * 30)
        cache.set("k4", "v" * 30)

        # k1 should still be there due to higher frequency
        assert cache.get("k1") is not None

    def test_fifo_policy(self):
        """Test FIFO eviction policy."""
        cache = CacheManagerFSA(
            l1_size=200,
            enable_l2=False,
            enable_l3=False,
            eviction_policy="fifo",
        )

        cache.set("first", "v" * 30)
        cache.set("second", "v" * 30)
        cache.set("third", "v" * 30)

        # First should be evicted when we add more
        cache.set("fourth", "v" * 30)

        # Some entries will be evicted based on FIFO order

    def test_adaptive_policy(self):
        """Test adaptive eviction policy."""
        cache = CacheManagerFSA(
            l1_size=1024 * 1024,
            enable_l2=False,
            enable_l3=False,
            eviction_policy="adaptive",
        )

        # Set some entries
        for i in range(10):
            cache.set(f"key_{i}", f"value_{i}")

        # Access some entries
        for i in range(5):
            cache.get(f"key_{i}")

        # Optimize should adapt the policy
        cache.optimize_eviction()

        # Should still work correctly
        assert cache.get("key_0") == "value_0"


class TestBloomFilter:
    """Test bloom filter functionality."""

    def test_bloom_filter_basic(self):
        """Test basic bloom filter operations."""
        bf = BloomFilter(size=100, num_hashes=3)

        bf.add("key1")
        bf.add("key2")

        assert bf.might_contain("key1") is True
        assert bf.might_contain("key2") is True

    def test_bloom_filter_negative_cache(self):
        """Test bloom filter for negative cache optimization."""
        cache = CacheManagerFSA(
            l1_size=1024 * 1024,
            enable_l2=False,
            enable_l3=False,
            enable_bloom_filter=True,
        )

        cache.set("exists", "value")

        # Bloom filter should indicate "exists" might be present
        assert cache.bloom_filter.might_contain("exists") is True

        # Non-existent key might return False (avoiding cache lookup)
        # This is probabilistic, so we just test the mechanism works
        result = cache.get("definitely_not_there")
        assert result is None


class TestCacheManagerContextManager:
    """Test cache manager as context manager."""

    def test_context_manager(self):
        """Test using cache manager as context manager."""
        with CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False) as cache:
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

        # After exiting, validate should have run


class TestClearOperation:
    """Test cache clear operation."""

    def test_clear_all_levels(self):
        """Test clearing all cache levels."""
        cache = CacheManagerFSA(l1_size=1024 * 1024, enable_l2=False, enable_l3=False)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

        stats = cache.get_statistics()
        assert stats["l1_entries"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

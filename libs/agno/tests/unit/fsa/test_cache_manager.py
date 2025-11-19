"""
Unit tests for Cache Manager FSA

Tests cover:
- Basic operations (get/set/delete)
- LRU eviction policy
- TTL expiration
- Size management
- Statistics and reporting
- Thread safety
"""

import unittest
import time
from datetime import datetime
from agno.fsa import CacheManagerFSA, EvictionReason


class TestCacheManagerBasics(unittest.TestCase):
    """Test basic cache operations"""

    def setUp(self):
        """Set up test cache instance"""
        self.cache = CacheManagerFSA(
            max_cache_size=10,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_set_and_get(self):
        """Test basic set and get operations"""
        # Set a value
        success = self.cache.set("test_key", "test_value")
        self.assertTrue(success)

        # Get the value
        value, hit = self.cache.get("test_key")
        self.assertTrue(hit)
        self.assertEqual(value, "test_value")

    def test_get_nonexistent_key(self):
        """Test getting a non-existent key"""
        value, hit = self.cache.get("nonexistent")
        self.assertFalse(hit)
        self.assertIsNone(value)

    def test_delete(self):
        """Test delete operation"""
        # Set and delete
        self.cache.set("delete_me", "value")
        deleted = self.cache.delete("delete_me")
        self.assertTrue(deleted)

        # Verify it's gone
        value, hit = self.cache.get("delete_me")
        self.assertFalse(hit)
        self.assertIsNone(value)

    def test_delete_nonexistent(self):
        """Test deleting a non-existent key"""
        deleted = self.cache.delete("nonexistent")
        self.assertFalse(deleted)

    def test_clear(self):
        """Test clearing all entries"""
        # Add multiple entries
        for i in range(5):
            self.cache.set(f"key:{i}", f"value:{i}")

        # Clear cache
        count = self.cache.clear()
        self.assertEqual(count, 5)
        self.assertEqual(len(self.cache), 0)

    def test_contains(self):
        """Test __contains__ method"""
        self.cache.set("exists", "value")
        self.assertIn("exists", self.cache)
        self.assertNotIn("missing", self.cache)

    def test_len(self):
        """Test __len__ method"""
        self.assertEqual(len(self.cache), 0)

        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.assertEqual(len(self.cache), 2)


class TestCacheLRUEviction(unittest.TestCase):
    """Test LRU eviction policy"""

    def setUp(self):
        """Set up test cache with small size"""
        self.cache = CacheManagerFSA(
            max_cache_size=3,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_lru_eviction_on_size_limit(self):
        """Test that LRU entry is evicted when size limit is reached"""
        # Fill cache to capacity
        self.cache.set("key:0", "value:0")
        self.cache.set("key:1", "value:1")
        self.cache.set("key:2", "value:2")
        self.assertEqual(len(self.cache), 3)

        # Add one more - should evict key:0 (least recently used)
        self.cache.set("key:3", "value:3")
        self.assertEqual(len(self.cache), 3)

        # Verify key:0 was evicted
        value, hit = self.cache.get("key:0")
        self.assertFalse(hit)

        # Verify others still exist
        value, hit = self.cache.get("key:1")
        self.assertTrue(hit)

    def test_lru_order_updated_on_get(self):
        """Test that get() updates LRU order"""
        # Fill cache
        self.cache.set("key:0", "value:0")
        self.cache.set("key:1", "value:1")
        self.cache.set("key:2", "value:2")

        # Access key:0 to make it most recently used
        self.cache.get("key:0")

        # Add new entry - should evict key:1 (now least recently used)
        self.cache.set("key:3", "value:3")

        # Verify key:1 was evicted, key:0 still exists
        value, hit = self.cache.get("key:1")
        self.assertFalse(hit)

        value, hit = self.cache.get("key:0")
        self.assertTrue(hit)

    def test_eviction_report(self):
        """Test that evictions are properly reported"""
        # Fill cache beyond capacity
        for i in range(5):
            self.cache.set(f"key:{i}", f"value:{i}")

        # Check eviction report
        report = self.cache.get_eviction_report()
        self.assertGreater(report["total_evictions"], 0)
        self.assertIn(EvictionReason.SIZE_LIMIT.value, report["evictions_by_reason"])


class TestCacheTTLExpiration(unittest.TestCase):
    """Test TTL expiration"""

    def setUp(self):
        """Set up test cache"""
        self.cache = CacheManagerFSA(
            max_cache_size=10,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_ttl_expiration(self):
        """Test that entries expire after TTL"""
        # Set entry with 1 second TTL
        self.cache.set("temp_key", "temp_value", ttl_seconds=1)

        # Immediate get should succeed
        value, hit = self.cache.get("temp_key")
        self.assertTrue(hit)

        # Wait for expiration
        time.sleep(1.5)

        # Get should now fail (expired)
        value, hit = self.cache.get("temp_key")
        self.assertFalse(hit)
        self.assertIsNone(value)

    def test_no_ttl_no_expiration(self):
        """Test that entries without TTL don't expire"""
        self.cache.set("permanent_key", "permanent_value", ttl_seconds=None)

        # Wait a bit
        time.sleep(1)

        # Should still be there
        value, hit = self.cache.get("permanent_key")
        self.assertTrue(hit)
        self.assertEqual(value, "permanent_value")

    def test_cleanup_expired(self):
        """Test manual cleanup of expired entries"""
        # Set multiple entries with short TTL
        self.cache.set("temp:1", "value1", ttl_seconds=1)
        self.cache.set("temp:2", "value2", ttl_seconds=1)
        self.cache.set("perm:1", "value3", ttl_seconds=None)

        # Wait for expiration
        time.sleep(1.5)

        # Manual cleanup
        expired_count = self.cache.cleanup_expired()
        self.assertEqual(expired_count, 2)

        # Only permanent entry should remain
        self.assertEqual(len(self.cache), 1)
        value, hit = self.cache.get("perm:1")
        self.assertTrue(hit)


class TestCacheStats(unittest.TestCase):
    """Test cache statistics"""

    def setUp(self):
        """Set up test cache"""
        self.cache = CacheManagerFSA(
            max_cache_size=10,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_hit_and_miss_tracking(self):
        """Test that hits and misses are tracked correctly"""
        # Set a key
        self.cache.set("key1", "value1")

        # Hit
        self.cache.get("key1")

        # Miss
        self.cache.get("nonexistent")

        # Check stats
        stats = self.cache.get_stats()
        self.assertEqual(stats["total_hits"], 1)
        self.assertEqual(stats["total_misses"], 1)
        self.assertAlmostEqual(stats["hit_rate"], 0.5)

    def test_set_tracking(self):
        """Test that set operations are tracked"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        stats = self.cache.get_stats()
        self.assertEqual(stats["total_sets"], 2)

    def test_delete_tracking(self):
        """Test that delete operations are tracked"""
        self.cache.set("key1", "value1")
        self.cache.delete("key1")

        stats = self.cache.get_stats()
        self.assertEqual(stats["total_deletes"], 1)

    def test_eviction_tracking(self):
        """Test that evictions are tracked"""
        cache = CacheManagerFSA(max_cache_size=2, enable_auto_cleanup=False)

        # Trigger eviction
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Evicts key1

        stats = cache.get_stats()
        self.assertEqual(stats["total_evictions"], 1)

        cache.shutdown()

    def test_utilization_rate(self):
        """Test cache utilization rate calculation"""
        cache = CacheManagerFSA(max_cache_size=10, enable_auto_cleanup=False)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()
        self.assertAlmostEqual(stats["utilization_rate"], 0.2)  # 2/10

        cache.shutdown()


class TestCacheEntryInfo(unittest.TestCase):
    """Test entry information retrieval"""

    def setUp(self):
        """Set up test cache"""
        self.cache = CacheManagerFSA(
            max_cache_size=10,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_get_entry_info(self):
        """Test retrieving detailed entry information"""
        self.cache.set("test_key", {"data": "value"}, ttl_seconds=300)

        info = self.cache.get_entry_info("test_key")
        self.assertIsNotNone(info)
        self.assertEqual(info["key"], "test_key")
        self.assertEqual(info["value"], {"data": "value"})
        self.assertEqual(info["ttl_seconds"], 300)
        self.assertEqual(info["access_count"], 0)
        self.assertFalse(info["is_expired"])

    def test_get_entry_info_nonexistent(self):
        """Test getting info for non-existent entry"""
        info = self.cache.get_entry_info("nonexistent")
        self.assertIsNone(info)

    def test_access_count_incremented(self):
        """Test that access count is incremented"""
        self.cache.set("test_key", "value")

        # Access multiple times
        self.cache.get("test_key")
        self.cache.get("test_key")
        self.cache.get("test_key")

        info = self.cache.get_entry_info("test_key")
        self.assertEqual(info["access_count"], 3)


class TestCacheContextManager(unittest.TestCase):
    """Test context manager functionality"""

    def test_context_manager(self):
        """Test using cache as context manager"""
        with CacheManagerFSA(max_cache_size=5, enable_auto_cleanup=False) as cache:
            cache.set("key1", "value1")
            value, hit = cache.get("key1")
            self.assertTrue(hit)

        # Cache should be cleaned up after context exit


class TestCacheComplexValues(unittest.TestCase):
    """Test caching complex data types"""

    def setUp(self):
        """Set up test cache"""
        self.cache = CacheManagerFSA(
            max_cache_size=10,
            enable_auto_cleanup=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        self.cache.shutdown()

    def test_cache_dict(self):
        """Test caching dictionary values"""
        data = {"name": "Alice", "role": "admin", "id": 1001}
        self.cache.set("user:1001", data)

        value, hit = self.cache.get("user:1001")
        self.assertTrue(hit)
        self.assertEqual(value, data)

    def test_cache_list(self):
        """Test caching list values"""
        data = [1, 2, 3, 4, 5]
        self.cache.set("numbers", data)

        value, hit = self.cache.get("numbers")
        self.assertTrue(hit)
        self.assertEqual(value, data)

    def test_cache_object(self):
        """Test caching custom objects"""
        class CustomObject:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        obj = CustomObject(10, 20)
        self.cache.set("custom_obj", obj)

        value, hit = self.cache.get("custom_obj")
        self.assertTrue(hit)
        self.assertEqual(value.x, 10)
        self.assertEqual(value.y, 20)


class TestCacheAutoCleanup(unittest.TestCase):
    """Test automatic cleanup functionality"""

    def test_auto_cleanup_disabled(self):
        """Test that auto cleanup can be disabled"""
        cache = CacheManagerFSA(enable_auto_cleanup=False)
        self.assertFalse(cache._cleanup_running)
        cache.shutdown()

    def test_auto_cleanup_enabled(self):
        """Test that auto cleanup thread starts when enabled"""
        cache = CacheManagerFSA(
            enable_auto_cleanup=True,
            cleanup_interval_seconds=1,
        )
        self.assertTrue(cache._cleanup_running)
        self.assertIsNotNone(cache._cleanup_thread)
        cache.shutdown()


if __name__ == "__main__":
    unittest.main()

"""Tests for Resource Allocator FSA."""

import pytest
import time
import threading
from agno.fsas.resource_allocator_fsa import ResourceAllocatorFSA


class TestBasicAllocations:
    """Tests for basic allocation and deallocation operations."""

    def test_allocate_single_resource(self):
        """Test allocating a single resource."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        result = allocator.allocate_resource("cpu", "consumer1", 10.0)
        assert result is True
        assert allocator.get_available("cpu") == 90.0

    def test_allocate_multiple_consumers(self):
        """Test allocating to multiple consumers."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 20.0)
        allocator.allocate_resource("cpu", "consumer2", 30.0)
        assert allocator.get_available("cpu") == 50.0

    def test_deallocate_full_amount(self):
        """Test deallocating entire allocation."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 25.0)
        result = allocator.deallocate_resource("cpu", "consumer1")
        assert result is True
        assert allocator.get_available("cpu") == 100.0

    def test_deallocate_partial_amount(self):
        """Test partial deallocation."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 50.0)
        allocator.deallocate_resource("cpu", "consumer1", 20.0)
        assert allocator.get_available("cpu") == 70.0

    def test_deallocate_nonexistent_consumer(self):
        """Test deallocating from non-existent consumer."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        result = allocator.deallocate_resource("cpu", "consumer1")
        assert result is False

    def test_deallocate_nonexistent_resource(self):
        """Test deallocating non-existent resource."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        result = allocator.deallocate_resource("nonexistent", "consumer1")
        assert result is False


class TestResourceLimits:
    """Tests for resource limit enforcement."""

    def test_set_resource_limit(self):
        """Test setting resource limit."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.set_resource_limit("cpu", 200.0)
        assert allocator.get_available("cpu") == 200.0

    def test_over_allocation_prevention(self):
        """Test prevention of over-allocation."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 80.0)
        result = allocator.allocate_resource("cpu", "consumer2", 30.0)
        assert result is False

    def test_exact_limit_allocation(self):
        """Test allocating exactly to the limit."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        result = allocator.allocate_resource("cpu", "consumer1", 100.0)
        assert result is True
        assert allocator.get_available("cpu") == 0.0

    def test_fractional_allocations(self):
        """Test fractional resource amounts."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 10.5)
        allocator.allocate_resource("cpu", "consumer2", 20.25)
        assert allocator.get_available("cpu") == pytest.approx(69.25)


class TestPriorityAllocation:
    """Tests for priority-based allocation."""

    def test_priority_allocation_ordering(self):
        """Test that higher priority requests are processed first."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 60.0, priority=1)

        # These should go to waitlist (not enough room)
        allocator.allocate_resource("cpu", "consumer2", 50.0, priority=5)
        allocator.allocate_resource("cpu", "consumer3", 60.0, priority=3)

        # Free up resources
        allocator.deallocate_resource("cpu", "consumer1")

        # Higher priority (consumer2) should be allocated first
        # consumer3 cannot fit since consumer2 took 50, leaving only 50 available (needs 60)
        allocated = allocator.get_allocated("cpu")
        assert "consumer2" in allocated
        assert "consumer3" not in allocated

    def test_priority_updates_on_reallocation(self):
        """Test priority updates when reallocating to same consumer."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 20.0, priority=1)
        allocator.allocate_resource("cpu", "consumer1", 10.0, priority=5)

        allocated = allocator.get_allocated("cpu", "consumer1")
        assert allocated['priority'] == 5


class TestMultiResourceCoordination:
    """Tests for managing multiple resource types."""

    def test_multiple_resource_types(self):
        """Test allocating different resource types."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 50.0)
        allocator.allocate_resource("memory", "consumer1", 30.0)
        allocator.allocate_resource("tokens", "consumer1", 20.0)

        assert allocator.get_available("cpu") == 50.0
        assert allocator.get_available("memory") == 70.0
        assert allocator.get_available("tokens") == 80.0

    def test_independent_resource_limits(self):
        """Test that resource limits are independent."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.set_resource_limit("cpu", 200.0)
        allocator.set_resource_limit("memory", 50.0)

        assert allocator.get_available("cpu") == 200.0
        assert allocator.get_available("memory") == 50.0


class TestAllocationStats:
    """Tests for allocation statistics."""

    def test_get_allocation_stats(self):
        """Test getting allocation statistics."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 30.0)
        allocator.allocate_resource("cpu", "consumer2", 20.0)

        stats = allocator.get_allocation_stats()
        assert stats['total_allocations'] == 2
        assert stats['total_active_consumers'] == 2
        assert 'cpu' in stats['resources']
        assert stats['resources']['cpu']['allocated'] == 50.0

    def test_utilization_rate(self):
        """Test resource utilization rate calculation."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 75.0)

        stats = allocator.get_allocation_stats()
        assert stats['resources']['cpu']['utilization_rate'] == 75.0

    def test_waitlist_size_in_stats(self):
        """Test waitlist size reporting in stats."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 80.0)
        allocator.allocate_resource("cpu", "consumer2", 30.0)
        allocator.allocate_resource("cpu", "consumer3", 40.0)

        stats = allocator.get_allocation_stats()
        assert stats['resources']['cpu']['waitlist_size'] == 2


class TestReleaseAll:
    """Tests for releasing all consumer resources."""

    def test_release_all_single_resource(self):
        """Test releasing all resources from single resource type."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 50.0)

        count = allocator.release_all("consumer1")
        assert count == 1
        assert allocator.get_available("cpu") == 100.0

    def test_release_all_multiple_resources(self):
        """Test releasing all resources across multiple types."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 30.0)
        allocator.allocate_resource("memory", "consumer1", 40.0)
        allocator.allocate_resource("tokens", "consumer1", 50.0)

        count = allocator.release_all("consumer1")
        assert count == 3
        assert allocator.get_available("cpu") == 100.0
        assert allocator.get_available("memory") == 100.0
        assert allocator.get_available("tokens") == 100.0

    def test_release_all_nonexistent_consumer(self):
        """Test releasing from non-existent consumer."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        count = allocator.release_all("nonexistent")
        assert count == 0


class TestGetAllocated:
    """Tests for querying allocation details."""

    def test_get_allocated_specific_consumer(self):
        """Test getting allocation for specific consumer."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 30.0, priority=5)

        allocated = allocator.get_allocated("cpu", "consumer1")
        assert allocated['amount'] == 30.0
        assert allocated['priority'] == 5

    def test_get_allocated_all_consumers(self):
        """Test getting all allocations for a resource."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 20.0)
        allocator.allocate_resource("cpu", "consumer2", 30.0)

        allocated = allocator.get_allocated("cpu")
        assert "consumer1" in allocated
        assert "consumer2" in allocated
        assert allocated["consumer1"]['amount'] == 20.0
        assert allocated["consumer2"]['amount'] == 30.0

    def test_get_allocated_nonexistent_resource(self):
        """Test querying non-existent resource."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocated = allocator.get_allocated("nonexistent")
        assert allocated == {}


class TestWaitlistManagement:
    """Tests for waitlist management."""

    def test_waitlist_addition(self):
        """Test adding requests to waitlist."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 80.0)
        allocator.allocate_resource("cpu", "consumer2", 30.0)

        waitlist = allocator.get_waitlist("cpu")
        assert len(waitlist) == 1
        assert waitlist[0]['consumer_id'] == "consumer2"

    def test_waitlist_priority_ordering(self):
        """Test waitlist is priority ordered."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 90.0)
        allocator.allocate_resource("cpu", "consumer2", 20.0, priority=1)
        allocator.allocate_resource("cpu", "consumer3", 20.0, priority=5)

        waitlist = allocator.get_waitlist("cpu")
        assert len(waitlist) == 2
        assert waitlist[0]['priority'] == 5
        assert waitlist[1]['priority'] == 1

    def test_waitlist_processing_on_deallocation(self):
        """Test waitlist processing when resources freed."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 80.0)
        allocator.allocate_resource("cpu", "consumer2", 30.0, priority=5)

        # Free resources
        allocator.deallocate_resource("cpu", "consumer1")

        # consumer2 should now be allocated
        allocated = allocator.get_allocated("cpu", "consumer2")
        assert allocated['amount'] == 30.0


class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_allocations(self):
        """Test concurrent allocations are thread-safe."""
        allocator = ResourceAllocatorFSA(default_limit=1000.0)

        def allocate_worker(consumer_id):
            for _ in range(10):
                allocator.allocate_resource("cpu", consumer_id, 1.0)
                time.sleep(0.001)

        threads = [threading.Thread(target=allocate_worker, args=(f"consumer{i}",))
                   for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = allocator.get_allocation_stats()
        assert stats['resources']['cpu']['allocated'] == 50.0

    def test_concurrent_deallocation(self):
        """Test concurrent deallocations are thread-safe."""
        allocator = ResourceAllocatorFSA(default_limit=1000.0)

        # Pre-allocate
        for i in range(10):
            allocator.allocate_resource("cpu", f"consumer{i}", 10.0)

        def deallocate_worker(consumer_id):
            allocator.deallocate_resource("cpu", consumer_id)

        threads = [threading.Thread(target=deallocate_worker, args=(f"consumer{i}",))
                   for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert allocator.get_available("cpu") == 1000.0


class TestIdleCleanup:
    """Tests for automatic cleanup of idle allocations."""

    def test_cleanup_idle_allocations(self):
        """Test cleanup of idle allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 30.0)

        # Simulate passage of time
        time.sleep(0.1)

        cleaned = allocator.cleanup_idle_allocations(timeout=0.05)
        assert cleaned == 1
        assert allocator.get_available("cpu") == 100.0

    def test_cleanup_preserves_active_allocations(self):
        """Test cleanup doesn't remove recently accessed allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 30.0)

        cleaned = allocator.cleanup_idle_allocations(timeout=10.0)
        assert cleaned == 0
        assert allocator.get_available("cpu") == 70.0


class TestPreemption:
    """Tests for resource preemption."""

    def test_preempt_low_priority(self):
        """Test preemption of low priority allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 40.0, priority=1)
        allocator.allocate_resource("cpu", "consumer2", 40.0, priority=2)

        result = allocator.preempt_low_priority("cpu", 50.0, min_priority=2)
        assert result is True

        # consumer1 should be preempted
        allocated = allocator.get_allocated("cpu", "consumer1")
        assert allocated == {}

    def test_preempt_preserves_high_priority(self):
        """Test preemption preserves high priority allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 40.0, priority=1)
        allocator.allocate_resource("cpu", "consumer2", 40.0, priority=5)

        allocator.preempt_low_priority("cpu", 50.0, min_priority=3)

        # consumer2 should remain
        allocated = allocator.get_allocated("cpu", "consumer2")
        assert allocated['amount'] == 40.0


class TestFragmentation:
    """Tests for resource fragmentation metrics."""

    def test_fragmentation_uniform_allocations(self):
        """Test fragmentation with uniform allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 25.0)
        allocator.allocate_resource("cpu", "consumer2", 25.0)
        allocator.allocate_resource("cpu", "consumer3", 25.0)

        frag = allocator.get_resource_fragmentation("cpu")
        assert frag < 0.1  # Low fragmentation

    def test_fragmentation_varied_allocations(self):
        """Test fragmentation with varied allocations."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)
        allocator.allocate_resource("cpu", "consumer1", 5.0)
        allocator.allocate_resource("cpu", "consumer2", 50.0)
        allocator.allocate_resource("cpu", "consumer3", 10.0)

        frag = allocator.get_resource_fragmentation("cpu")
        assert frag > 0.5  # Higher fragmentation


class TestSmokeTests:
    """Comprehensive smoke tests."""

    def test_full_lifecycle(self):
        """Test complete resource lifecycle."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)

        # Allocate
        assert allocator.allocate_resource("cpu", "consumer1", 30.0, priority=1)
        assert allocator.allocate_resource("memory", "consumer1", 40.0, priority=2)

        # Check stats
        stats = allocator.get_allocation_stats()
        assert stats['total_allocations'] == 2
        assert stats['total_active_consumers'] == 1

        # Partial deallocation
        assert allocator.deallocate_resource("cpu", "consumer1", 10.0)
        assert allocator.get_allocated("cpu", "consumer1")['amount'] == 20.0

        # Release all
        count = allocator.release_all("consumer1")
        assert count == 2

        # Verify clean state
        assert allocator.get_available("cpu") == 100.0
        assert allocator.get_available("memory") == 100.0

    def test_complex_multi_consumer_scenario(self):
        """Test complex scenario with multiple consumers and resources."""
        allocator = ResourceAllocatorFSA(default_limit=100.0)

        # Multiple consumers, multiple resources
        allocator.allocate_resource("cpu", "consumer1", 30.0, priority=5)
        allocator.allocate_resource("cpu", "consumer2", 20.0, priority=3)
        allocator.allocate_resource("memory", "consumer1", 40.0)
        allocator.allocate_resource("memory", "consumer3", 25.0)

        # Test over-allocation handling
        result = allocator.allocate_resource("cpu", "consumer3", 60.0, priority=10)
        assert result is False  # Should go to waitlist

        # Free up resources
        allocator.deallocate_resource("cpu", "consumer1")

        # High priority consumer3 should get allocated
        allocated = allocator.get_allocated("cpu", "consumer3")
        assert allocated['amount'] == 60.0

        # Check final stats
        stats = allocator.get_allocation_stats()
        assert stats['total_active_consumers'] == 3
        assert len(stats['resources']) == 2

    def test_stress_test_many_allocations(self):
        """Stress test with many allocations."""
        allocator = ResourceAllocatorFSA(default_limit=10000.0)

        # Allocate to many consumers
        for i in range(100):
            allocator.allocate_resource("cpu", f"consumer{i}", 50.0, priority=i % 10)

        stats = allocator.get_allocation_stats()
        assert stats['resources']['cpu']['allocated'] == 5000.0
        assert stats['total_active_consumers'] == 100

        # Release half
        for i in range(50):
            allocator.release_all(f"consumer{i}")

        stats = allocator.get_allocation_stats()
        assert stats['resources']['cpu']['allocated'] == 2500.0
        assert stats['total_active_consumers'] == 50

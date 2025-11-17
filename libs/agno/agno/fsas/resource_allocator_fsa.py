"""Resource Allocator FSA - Computational resource allocation and management system."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from queue import PriorityQueue


@dataclass
class AllocationRecord:
    """Tracks individual resource allocation."""
    amount: float
    priority: int
    timestamp: float
    last_accessed: float

    def touch(self):
        """Update last accessed timestamp."""
        self.last_accessed = time.time()


@dataclass
class ResourcePool:
    """Manages a single resource type."""
    limit: float
    allocated: float = 0.0
    allocations: Dict[str, AllocationRecord] = field(default_factory=dict)
    waitlist: List[Tuple[int, float, str, float]] = field(default_factory=list)

    def available(self) -> float:
        """Returns available resource amount."""
        return max(0.0, self.limit - self.allocated)

    def utilization_rate(self) -> float:
        """Returns resource utilization percentage."""
        if self.limit == 0:
            return 0.0
        return (self.allocated / self.limit) * 100.0


class ResourceAllocatorFSA:
    """
    Finite State Automation for computational resource allocation and management.

    Manages allocation of computational resources (CPU, memory, tokens, etc.) across
    multiple consumers with priority-based allocation, quotas, and automatic reclamation.
    """

    def __init__(self, default_limit: float = 100.0):
        """
        Initialize ResourceAllocatorFSA.

        Args:
            default_limit: Default resource limit for new resource types
        """
        self._resources: Dict[str, ResourcePool] = {}
        self._default_limit = default_limit
        self._lock = threading.Lock()
        self._allocation_history: List[Dict] = []
        self._total_allocations = 0
        self._total_deallocations = 0
        self._idle_timeout = 300.0  # 5 minutes default

    def allocate_resource(
        self,
        resource_id: str,
        consumer_id: str,
        amount: float,
        priority: int = 0
    ) -> bool:
        """
        Allocates resources to a consumer.

        Args:
            resource_id: Identifier for the resource type
            consumer_id: Identifier for the consumer
            amount: Amount of resource to allocate
            priority: Allocation priority (higher = more important)

        Returns:
            True if allocation successful, False otherwise
        """
        with self._lock:
            # Initialize resource pool if needed
            if resource_id not in self._resources:
                self._resources[resource_id] = ResourcePool(limit=self._default_limit)

            pool = self._resources[resource_id]

            # Check if enough resources available
            if pool.available() < amount:
                # Add to waitlist
                pool.waitlist.append((-priority, time.time(), consumer_id, amount))
                pool.waitlist.sort()
                return False

            # Allocate resource
            if consumer_id in pool.allocations:
                # Update existing allocation
                record = pool.allocations[consumer_id]
                pool.allocated -= record.amount
                record.amount += amount
                record.priority = max(record.priority, priority)
                record.touch()
                pool.allocated += record.amount
            else:
                # Create new allocation
                pool.allocations[consumer_id] = AllocationRecord(
                    amount=amount,
                    priority=priority,
                    timestamp=time.time(),
                    last_accessed=time.time()
                )
                pool.allocated += amount

            self._total_allocations += 1
            self._allocation_history.append({
                'action': 'allocate',
                'resource_id': resource_id,
                'consumer_id': consumer_id,
                'amount': amount,
                'priority': priority,
                'timestamp': time.time()
            })

            # Try to process waitlist
            self._process_waitlist(resource_id)

            return True

    def deallocate_resource(
        self,
        resource_id: str,
        consumer_id: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Releases resources from a consumer.

        Args:
            resource_id: Identifier for the resource type
            consumer_id: Identifier for the consumer
            amount: Amount to deallocate (None = all)

        Returns:
            True if deallocation successful, False otherwise
        """
        with self._lock:
            if resource_id not in self._resources:
                return False

            pool = self._resources[resource_id]

            if consumer_id not in pool.allocations:
                return False

            record = pool.allocations[consumer_id]

            if amount is None or amount >= record.amount:
                # Deallocate all
                pool.allocated -= record.amount
                deallocated = record.amount
                del pool.allocations[consumer_id]
            else:
                # Partial deallocation
                record.amount -= amount
                pool.allocated -= amount
                deallocated = amount
                record.touch()

            self._total_deallocations += 1
            self._allocation_history.append({
                'action': 'deallocate',
                'resource_id': resource_id,
                'consumer_id': consumer_id,
                'amount': deallocated,
                'timestamp': time.time()
            })

            # Try to process waitlist
            self._process_waitlist(resource_id)

            return True

    def get_available(self, resource_id: str) -> float:
        """
        Returns available resource amount.

        Args:
            resource_id: Identifier for the resource type

        Returns:
            Available amount of the resource
        """
        with self._lock:
            if resource_id not in self._resources:
                return self._default_limit
            return self._resources[resource_id].available()

    def get_allocated(
        self,
        resource_id: str,
        consumer_id: Optional[str] = None
    ) -> Dict:
        """
        Returns allocation details.

        Args:
            resource_id: Identifier for the resource type
            consumer_id: Optional consumer identifier

        Returns:
            Dictionary with allocation details
        """
        with self._lock:
            if resource_id not in self._resources:
                return {}

            pool = self._resources[resource_id]

            if consumer_id:
                if consumer_id not in pool.allocations:
                    return {}
                record = pool.allocations[consumer_id]
                return {
                    'consumer_id': consumer_id,
                    'amount': record.amount,
                    'priority': record.priority,
                    'timestamp': record.timestamp,
                    'last_accessed': record.last_accessed
                }
            else:
                # Return all allocations
                return {
                    cid: {
                        'amount': rec.amount,
                        'priority': rec.priority,
                        'timestamp': rec.timestamp,
                        'last_accessed': rec.last_accessed
                    }
                    for cid, rec in pool.allocations.items()
                }

    def set_resource_limit(self, resource_id: str, limit: float) -> None:
        """
        Sets maximum resource limit.

        Args:
            resource_id: Identifier for the resource type
            limit: Maximum resource limit
        """
        with self._lock:
            if resource_id not in self._resources:
                self._resources[resource_id] = ResourcePool(limit=limit)
            else:
                self._resources[resource_id].limit = limit
                # Try to process waitlist with new limit
                self._process_waitlist(resource_id)

    def get_allocation_stats(self) -> Dict:
        """
        Returns allocation statistics.

        Returns:
            Dictionary with comprehensive allocation statistics
        """
        with self._lock:
            stats = {
                'total_allocations': self._total_allocations,
                'total_deallocations': self._total_deallocations,
                'active_consumers': set(),
                'resources': {}
            }

            for resource_id, pool in self._resources.items():
                stats['resources'][resource_id] = {
                    'limit': pool.limit,
                    'allocated': pool.allocated,
                    'available': pool.available(),
                    'utilization_rate': pool.utilization_rate(),
                    'num_consumers': len(pool.allocations),
                    'waitlist_size': len(pool.waitlist),
                    'allocations': {
                        cid: rec.amount
                        for cid, rec in pool.allocations.items()
                    }
                }
                stats['active_consumers'].update(pool.allocations.keys())

            stats['active_consumers'] = list(stats['active_consumers'])
            stats['total_active_consumers'] = len(stats['active_consumers'])

            return stats

    def release_all(self, consumer_id: str) -> int:
        """
        Releases all resources held by a consumer.

        Args:
            consumer_id: Identifier for the consumer

        Returns:
            Number of resources released
        """
        with self._lock:
            released_count = 0

            for resource_id, pool in self._resources.items():
                if consumer_id in pool.allocations:
                    record = pool.allocations[consumer_id]
                    pool.allocated -= record.amount

                    self._allocation_history.append({
                        'action': 'release_all',
                        'resource_id': resource_id,
                        'consumer_id': consumer_id,
                        'amount': record.amount,
                        'timestamp': time.time()
                    })

                    del pool.allocations[consumer_id]
                    released_count += 1
                    self._total_deallocations += 1

                    # Try to process waitlist
                    self._process_waitlist(resource_id)

            return released_count

    def _process_waitlist(self, resource_id: str) -> None:
        """Process pending allocation requests from waitlist."""
        if resource_id not in self._resources:
            return

        pool = self._resources[resource_id]

        if not pool.waitlist:
            return

        # Process waitlist in priority order
        processed = []
        for i, (neg_priority, timestamp, consumer_id, amount) in enumerate(pool.waitlist):
            if pool.available() >= amount:
                # Can allocate
                priority = -neg_priority
                if consumer_id in pool.allocations:
                    record = pool.allocations[consumer_id]
                    pool.allocated -= record.amount
                    record.amount += amount
                    record.priority = max(record.priority, priority)
                    record.touch()
                    pool.allocated += record.amount
                else:
                    pool.allocations[consumer_id] = AllocationRecord(
                        amount=amount,
                        priority=priority,
                        timestamp=time.time(),
                        last_accessed=time.time()
                    )
                    pool.allocated += amount

                self._total_allocations += 1
                self._allocation_history.append({
                    'action': 'allocate_from_waitlist',
                    'resource_id': resource_id,
                    'consumer_id': consumer_id,
                    'amount': amount,
                    'priority': priority,
                    'timestamp': time.time()
                })

                processed.append(i)

        # Remove processed items from waitlist
        for i in reversed(processed):
            pool.waitlist.pop(i)

    def cleanup_idle_allocations(self, timeout: Optional[float] = None) -> int:
        """
        Remove allocations that haven't been accessed recently.

        Args:
            timeout: Idle timeout in seconds (uses default if None)

        Returns:
            Number of allocations cleaned up
        """
        timeout = timeout if timeout is not None else self._idle_timeout
        current_time = time.time()
        cleaned = 0

        with self._lock:
            for resource_id, pool in self._resources.items():
                to_remove = []

                for consumer_id, record in pool.allocations.items():
                    if current_time - record.last_accessed > timeout:
                        to_remove.append(consumer_id)

                for consumer_id in to_remove:
                    record = pool.allocations[consumer_id]
                    pool.allocated -= record.amount
                    del pool.allocations[consumer_id]
                    cleaned += 1

                    self._allocation_history.append({
                        'action': 'cleanup_idle',
                        'resource_id': resource_id,
                        'consumer_id': consumer_id,
                        'amount': record.amount,
                        'timestamp': time.time()
                    })

                # Process waitlist after cleanup
                if to_remove:
                    self._process_waitlist(resource_id)

        return cleaned

    def get_waitlist(self, resource_id: str) -> List[Dict]:
        """
        Get pending allocation requests for a resource.

        Args:
            resource_id: Identifier for the resource type

        Returns:
            List of waitlist entries
        """
        with self._lock:
            if resource_id not in self._resources:
                return []

            pool = self._resources[resource_id]
            return [
                {
                    'priority': -neg_priority,
                    'timestamp': timestamp,
                    'consumer_id': consumer_id,
                    'amount': amount
                }
                for neg_priority, timestamp, consumer_id, amount in pool.waitlist
            ]

    def preempt_low_priority(
        self,
        resource_id: str,
        required_amount: float,
        min_priority: int
    ) -> bool:
        """
        Preempt lower priority allocations to free resources.

        Args:
            resource_id: Identifier for the resource type
            required_amount: Amount of resource needed
            min_priority: Minimum priority to keep

        Returns:
            True if enough resources freed, False otherwise
        """
        with self._lock:
            if resource_id not in self._resources:
                return False

            pool = self._resources[resource_id]

            if pool.available() >= required_amount:
                return True

            # Find allocations to preempt
            preemptable = [
                (consumer_id, record)
                for consumer_id, record in pool.allocations.items()
                if record.priority < min_priority
            ]

            # Sort by priority (lowest first)
            preemptable.sort(key=lambda x: x[1].priority)

            freed = 0.0
            for consumer_id, record in preemptable:
                if pool.available() + freed >= required_amount:
                    break

                pool.allocated -= record.amount
                freed += record.amount

                self._allocation_history.append({
                    'action': 'preempt',
                    'resource_id': resource_id,
                    'consumer_id': consumer_id,
                    'amount': record.amount,
                    'timestamp': time.time()
                })

                del pool.allocations[consumer_id]
                self._total_deallocations += 1

            return pool.available() >= required_amount

    def get_resource_fragmentation(self, resource_id: str) -> float:
        """
        Calculate resource fragmentation (allocation spread).

        Args:
            resource_id: Identifier for the resource type

        Returns:
            Fragmentation score (0-1, higher = more fragmented)
        """
        with self._lock:
            if resource_id not in self._resources:
                return 0.0

            pool = self._resources[resource_id]

            if not pool.allocations or pool.allocated == 0:
                return 0.0

            # Calculate variance in allocation sizes
            allocations = [rec.amount for rec in pool.allocations.values()]
            n = len(allocations)

            if n == 1:
                return 0.0

            mean = sum(allocations) / n
            variance = sum((x - mean) ** 2 for x in allocations) / n
            std_dev = variance ** 0.5

            # Normalize by mean to get coefficient of variation
            if mean == 0:
                return 0.0

            cv = std_dev / mean
            # Normalize to 0-1 range (cap at 1.0)
            return min(cv, 1.0)

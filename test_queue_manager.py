"""Test script for Queue Manager FSA."""
import sys
sys.path.insert(0, '/home/user/agno/libs/agno')
from agno.queue import QueueManager, QueueState, QueueTask

def test_queue_manager():
    """Test basic queue manager FSA operations."""
    qm = QueueManager()

    # Test 1: Add tasks
    task1 = QueueTask(task_id="task1", payload={"data": "test1"})
    task2 = QueueTask(task_id="task2", payload={"data": "test2"})

    assert qm.add_task(task1), "Failed to add task1"
    assert qm.add_task(task2), "Failed to add task2"
    assert qm.get_state("task1") == QueueState.QUEUED, "Task1 should be QUEUED"
    print("✓ Task addition and queuing works")

    # Test 2: Process task
    next_task = qm.process_next()
    assert next_task is not None, "Should return task1"
    assert next_task.task_id == "task1", "Should be task1"
    assert qm.get_state("task1") == QueueState.PROCESSING, "Task1 should be PROCESSING"
    print("✓ Task processing works")

    # Test 3: Complete task
    assert qm.complete_task("task1", result="success"), "Failed to complete task1"
    assert qm.get_state("task1") == QueueState.COMPLETED, "Task1 should be COMPLETED"
    print("✓ Task completion works")

    # Test 4: Fail task
    next_task = qm.process_next()
    assert next_task.task_id == "task2", "Should be task2"
    assert qm.fail_task("task2", error="Test error"), "Failed to fail task2"
    assert qm.get_state("task2") == QueueState.FAILED, "Task2 should be FAILED"
    print("✓ Task failure works")

    # Test 5: Retry failed task
    assert qm.transition("task2", QueueState.QUEUED), "Failed to retry task2"
    assert qm.get_state("task2") == QueueState.QUEUED, "Task2 should be QUEUED again"
    print("✓ Task retry works")

    # Test 6: State transition validation
    assert not qm.transition("task1", QueueState.PROCESSING), "Should not allow COMPLETED -> PROCESSING"
    print("✓ Invalid transition blocked")

    # Test 7: Handler registration
    handled_states = []
    def handler(task):
        handled_states.append(task.state)

    qm.register_handler(QueueState.PROCESSING, handler)
    task3 = QueueTask(task_id="task3", payload={"data": "test3"})
    qm.add_task(task3)
    qm.process_next()
    assert QueueState.PROCESSING in handled_states, "Handler should be called"
    print("✓ State handler works")

    print("\n✅ All tests passed! Queue Manager FSA is working correctly.")

if __name__ == "__main__":
    test_queue_manager()

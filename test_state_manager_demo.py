#!/usr/bin/env python3
"""
Demo script to test StateManagerFSA functionality
This script demonstrates and validates the key features of the State Manager FSA
"""

import sys
import tempfile
from pathlib import Path

# Add libs/agno to the path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "agno"))

from agno.state_manager_fsa import (
    StateManagerFSA,
    TaskState,
    CheckpointConfig,
    StateVersion
)


def print_section(title):
    """Print a section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_basic_operations():
    """Test basic state manager operations"""
    print_section("Test 1: Basic Task Operations")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create FSM instance
        config = CheckpointConfig(auto_checkpoint=False)
        fsm = StateManagerFSA(storage_path=tmpdir, checkpoint_config=config)

        # Create task
        task = fsm.create_task(
            task_id="demo_task_1",
            data={"name": "Process data", "value": 42},
            metadata={"priority": "high"}
        )
        print(f"✓ Created task: {task.task_id}")
        print(f"  State: {task.current_state.value}")
        print(f"  Data: {task.data}")

        # Transition states
        fsm.transition_state("demo_task_1", TaskState.IN_PROGRESS)
        print(f"✓ Transitioned to: {fsm.get_task('demo_task_1').current_state.value}")

        fsm.transition_state("demo_task_1", TaskState.COMPLETED)
        print(f"✓ Transitioned to: {fsm.get_task('demo_task_1').current_state.value}")

        print("\n✅ Basic operations test PASSED")


def test_save_load():
    """Test state persistence"""
    print_section("Test 2: State Save/Load")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and save state
        fsm1 = StateManagerFSA(storage_path=tmpdir)
        fsm1.create_task("persist_task", data={"counter": 100})
        fsm1.transition_state("persist_task", TaskState.IN_PROGRESS)
        file_path = fsm1.save_state("persist_task")
        print(f"✓ Saved state to: {file_path}")

        # Load state in new FSM
        fsm2 = StateManagerFSA(storage_path=tmpdir)
        loaded_task = fsm2.load_state("persist_task")
        print(f"✓ Loaded task: {loaded_task.task_id}")
        print(f"  State: {loaded_task.current_state.value}")
        print(f"  Data: {loaded_task.data}")

        # Verify data matches
        assert loaded_task.task_id == "persist_task"
        assert loaded_task.current_state == TaskState.IN_PROGRESS
        assert loaded_task.data["counter"] == 100

        print("\n✅ Save/Load test PASSED")


def test_checkpoints():
    """Test checkpoint management"""
    print_section("Test 3: Checkpoint Management")

    with tempfile.TemporaryDirectory() as tmpdir:
        fsm = StateManagerFSA(storage_path=tmpdir)
        fsm.create_task("checkpoint_task", data={"progress": 0})
        fsm.transition_state("checkpoint_task", TaskState.IN_PROGRESS)

        # Create checkpoints
        for i in range(3):
            task = fsm.get_task("checkpoint_task")
            task.data["progress"] = (i + 1) * 33
            checkpoint = fsm.create_checkpoint("checkpoint_task")
            print(f"✓ Created checkpoint: {checkpoint.checkpoint_id}")
            print(f"  Progress: {task.data['progress']}%")

        # Modify data
        task = fsm.get_task("checkpoint_task")
        task.data["progress"] = 999
        print(f"\n  Modified progress to: {task.data['progress']}%")

        # Restore from checkpoint
        fsm.restore_checkpoint("checkpoint_task")
        restored_task = fsm.get_task("checkpoint_task")
        print(f"✓ Restored from checkpoint")
        print(f"  Progress after restore: {restored_task.data['progress']}%")
        print(f"  State: {restored_task.current_state.value}")

        assert restored_task.data["progress"] == 99  # Last checkpoint

        print("\n✅ Checkpoint test PASSED")


def test_recovery():
    """Test recovery mechanisms"""
    print_section("Test 4: Task Recovery")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and interrupt task
        fsm1 = StateManagerFSA(storage_path=tmpdir)
        fsm1.create_task("recovery_task", data={"step": "processing"})
        fsm1.transition_state("recovery_task", TaskState.IN_PROGRESS)
        fsm1.create_checkpoint("recovery_task")
        fsm1.save_state("recovery_task")
        print("✓ Created task and checkpoint")
        print("  Simulating interruption...")

        # Recover in new FSM instance
        fsm2 = StateManagerFSA(storage_path=tmpdir)
        success = fsm2.recover_task("recovery_task")
        print(f"✓ Recovery success: {success}")

        recovered_task = fsm2.get_task("recovery_task")
        print(f"  Recovered state: {recovered_task.current_state.value}")
        print(f"  Data: {recovered_task.data}")

        assert success is True
        assert recovered_task.current_state == TaskState.RECOVERING

        print("\n✅ Recovery test PASSED")


def test_state_transitions():
    """Test FSA state transition rules"""
    print_section("Test 5: State Transition Rules (FSA)")

    with tempfile.TemporaryDirectory() as tmpdir:
        fsm = StateManagerFSA(storage_path=tmpdir)
        fsm.create_task("transition_task", data={})

        # Valid transitions
        print("Testing valid transitions:")
        fsm.transition_state("transition_task", TaskState.IN_PROGRESS)
        print(f"  ✓ PENDING → IN_PROGRESS")

        fsm.transition_state("transition_task", TaskState.SUSPENDED)
        print(f"  ✓ IN_PROGRESS → SUSPENDED")

        fsm.transition_state("transition_task", TaskState.IN_PROGRESS)
        print(f"  ✓ SUSPENDED → IN_PROGRESS")

        fsm.transition_state("transition_task", TaskState.COMPLETED)
        print(f"  ✓ IN_PROGRESS → COMPLETED")

        # Invalid transition
        print("\nTesting invalid transition:")
        try:
            fsm.transition_state("transition_task", TaskState.IN_PROGRESS)
            print("  ✗ Should have raised error!")
            sys.exit(1)
        except RuntimeError as e:
            print(f"  ✓ Correctly rejected: COMPLETED → IN_PROGRESS")
            print(f"    Error: {str(e)}")

        print("\n✅ State transition test PASSED")


def test_versioning():
    """Test version compatibility"""
    print_section("Test 6: State Versioning")

    v1_0_0 = StateVersion(major=1, minor=0, patch=0)
    v1_0_1 = StateVersion(major=1, minor=0, patch=1)
    v2_0_0 = StateVersion(major=2, minor=0, patch=0)

    print(f"Version 1.0.0: {v1_0_0}")
    print(f"Version 1.0.1: {v1_0_1}")
    print(f"Version 2.0.0: {v2_0_0}")

    print("\nCompatibility checks:")
    print(f"  1.0.0 compatible with 1.0.1: {v1_0_0.is_compatible(v1_0_1)}")
    print(f"  1.0.0 compatible with 2.0.0: {v1_0_0.is_compatible(v2_0_0)}")

    assert v1_0_0.is_compatible(v1_0_1) is True
    assert v1_0_0.is_compatible(v2_0_0) is False

    print("\n✅ Versioning test PASSED")


def test_statistics():
    """Test statistics and utility functions"""
    print_section("Test 7: Statistics & Utilities")

    with tempfile.TemporaryDirectory() as tmpdir:
        fsm = StateManagerFSA(storage_path=tmpdir)

        # Create multiple tasks
        fsm.create_task("task_1", data={})
        fsm.create_task("task_2", data={})
        fsm.create_task("task_3", data={})

        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_2", TaskState.IN_PROGRESS)
        fsm.transition_state("task_2", TaskState.COMPLETED)

        fsm.create_checkpoint("task_1")
        fsm.create_checkpoint("task_3")

        # Get statistics
        stats = fsm.get_statistics()
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"State counts: {stats['state_counts']}")
        print(f"Total checkpoints: {stats['total_checkpoints']}")

        # Get tasks by state
        in_progress = fsm.get_all_tasks(state_filter=TaskState.IN_PROGRESS)
        print(f"\nTasks in IN_PROGRESS state: {len(in_progress)}")

        assert stats['total_tasks'] == 3
        assert stats['total_checkpoints'] == 2
        assert len(in_progress) == 1

        print("\n✅ Statistics test PASSED")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  STATE MANAGER FSA - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    try:
        test_basic_operations()
        test_save_load()
        test_checkpoints()
        test_recovery()
        test_state_transitions()
        test_versioning()
        test_statistics()

        print("\n" + "=" * 60)
        print("  ✅ ALL TESTS PASSED!")
        print("=" * 60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

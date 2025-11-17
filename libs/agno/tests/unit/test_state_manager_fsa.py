"""
Unit tests for State Manager FSA

Tests cover:
- Task creation and state transitions
- State save/load functionality
- Checkpoint management
- State recovery mechanisms
- Version migration
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from agno.state_manager_fsa import (
    Checkpoint,
    CheckpointConfig,
    StateManagerFSA,
    StateVersion,
    TaskState,
    TaskStateData,
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def fsm(temp_storage_dir):
    """Create StateManagerFSA instance for tests"""
    config = CheckpointConfig(
        auto_checkpoint=False,  # Disable auto-checkpoint for tests
        checkpoint_interval=0,
        max_checkpoints=5
    )
    return StateManagerFSA(storage_path=temp_storage_dir, checkpoint_config=config)


class TestTaskCreation:
    """Test task creation and basic operations"""

    def test_create_task(self, fsm):
        """Test creating a new task"""
        task = fsm.create_task(
            task_id="task_1",
            data={"name": "Test Task", "value": 42},
            metadata={"priority": "high"}
        )

        assert task.task_id == "task_1"
        assert task.current_state == TaskState.PENDING
        assert task.data == {"name": "Test Task", "value": 42}
        assert task.metadata == {"priority": "high"}
        assert task.retry_count == 0

    def test_create_duplicate_task(self, fsm):
        """Test that creating duplicate task raises error"""
        fsm.create_task("task_1", data={})

        with pytest.raises(ValueError, match="already exists"):
            fsm.create_task("task_1", data={})

    def test_get_task(self, fsm):
        """Test retrieving a task"""
        created_task = fsm.create_task("task_1", data={"test": "data"})
        retrieved_task = fsm.get_task("task_1")

        assert retrieved_task is not None
        assert retrieved_task.task_id == created_task.task_id
        assert retrieved_task.data == created_task.data

    def test_get_nonexistent_task(self, fsm):
        """Test retrieving nonexistent task returns None"""
        task = fsm.get_task("nonexistent")
        assert task is None


class TestStateTransitions:
    """Test state transition logic (FSA)"""

    def test_valid_transition_pending_to_in_progress(self, fsm):
        """Test valid transition from PENDING to IN_PROGRESS"""
        fsm.create_task("task_1", data={})
        success = fsm.transition_state("task_1", TaskState.IN_PROGRESS)

        assert success is True
        task = fsm.get_task("task_1")
        assert task.current_state == TaskState.IN_PROGRESS
        assert task.previous_state == TaskState.PENDING

    def test_valid_transition_in_progress_to_completed(self, fsm):
        """Test valid transition from IN_PROGRESS to COMPLETED"""
        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_1", TaskState.COMPLETED)

        task = fsm.get_task("task_1")
        assert task.current_state == TaskState.COMPLETED
        assert task.previous_state == TaskState.IN_PROGRESS

    def test_valid_transition_in_progress_to_failed(self, fsm):
        """Test valid transition from IN_PROGRESS to FAILED with error message"""
        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_1", TaskState.FAILED, error_message="Connection timeout")

        task = fsm.get_task("task_1")
        assert task.current_state == TaskState.FAILED
        assert task.error_message == "Connection timeout"
        assert task.retry_count == 1

    def test_invalid_transition_completed_to_in_progress(self, fsm):
        """Test that invalid transition raises error"""
        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_1", TaskState.COMPLETED)

        with pytest.raises(RuntimeError, match="Invalid state transition"):
            fsm.transition_state("task_1", TaskState.IN_PROGRESS)

    def test_transition_failed_to_recovering(self, fsm):
        """Test transition from FAILED to RECOVERING"""
        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_1", TaskState.FAILED)
        fsm.transition_state("task_1", TaskState.RECOVERING)

        task = fsm.get_task("task_1")
        assert task.current_state == TaskState.RECOVERING

    def test_transition_nonexistent_task(self, fsm):
        """Test transitioning nonexistent task raises error"""
        with pytest.raises(ValueError, match="not found"):
            fsm.transition_state("nonexistent", TaskState.IN_PROGRESS)


class TestStatePersistence:
    """Test state save/load functionality"""

    def test_save_state(self, fsm):
        """Test saving task state to disk"""
        fsm.create_task("task_1", data={"key": "value"})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)

        file_path = fsm.save_state("task_1")

        assert os.path.exists(file_path)
        assert file_path.endswith("task_1.json")

        # Verify file contents
        with open(file_path, 'r') as f:
            saved_data = json.load(f)

        assert "version" in saved_data
        assert "task" in saved_data
        assert saved_data["task"]["task_id"] == "task_1"
        assert saved_data["task"]["current_state"] == TaskState.IN_PROGRESS.value

    def test_load_state(self, fsm, temp_storage_dir):
        """Test loading task state from disk"""
        # Create and save task
        fsm.create_task("task_1", data={"key": "value"}, metadata={"test": "meta"})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.save_state("task_1")

        # Create new FSM instance and load state
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        loaded_task = new_fsm.load_state("task_1")

        assert loaded_task is not None
        assert loaded_task.task_id == "task_1"
        assert loaded_task.current_state == TaskState.IN_PROGRESS
        assert loaded_task.data == {"key": "value"}
        assert loaded_task.metadata == {"test": "meta"}

    def test_load_nonexistent_state(self, fsm):
        """Test loading nonexistent state returns None"""
        task = fsm.load_state("nonexistent")
        assert task is None

    def test_save_nonexistent_task(self, fsm):
        """Test saving nonexistent task raises error"""
        with pytest.raises(ValueError, match="not found"):
            fsm.save_state("nonexistent")


class TestCheckpointManagement:
    """Test checkpoint creation and restoration"""

    def test_create_checkpoint(self, fsm):
        """Test creating a checkpoint"""
        fsm.create_task("task_1", data={"counter": 0})
        checkpoint = fsm.create_checkpoint("task_1", metadata={"note": "initial"})

        assert checkpoint.task_id == "task_1"
        assert checkpoint.state == TaskState.PENDING
        assert checkpoint.data == {"counter": 0}
        assert checkpoint.metadata == {"note": "initial"}

        task = fsm.get_task("task_1")
        assert len(task.checkpoints) == 1

    def test_multiple_checkpoints(self, fsm):
        """Test creating multiple checkpoints"""
        fsm.create_task("task_1", data={"counter": 0})

        # Create multiple checkpoints
        for i in range(3):
            fsm.create_checkpoint("task_1", checkpoint_id=f"cp_{i}")
            time.sleep(0.01)  # Small delay to ensure different timestamps

        task = fsm.get_task("task_1")
        assert len(task.checkpoints) == 3
        assert task.checkpoints[0].checkpoint_id == "cp_0"
        assert task.checkpoints[2].checkpoint_id == "cp_2"

    def test_checkpoint_limit(self, fsm):
        """Test that checkpoints are limited to max_checkpoints"""
        fsm.create_task("task_1", data={"counter": 0})

        # Create more checkpoints than the limit (5)
        for i in range(10):
            fsm.create_checkpoint("task_1")
            time.sleep(0.01)

        task = fsm.get_task("task_1")
        assert len(task.checkpoints) == 5  # Should only keep last 5

    def test_restore_checkpoint(self, fsm):
        """Test restoring from checkpoint"""
        fsm.create_task("task_1", data={"counter": 0})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)

        # Create checkpoint at counter=0
        cp1 = fsm.create_checkpoint("task_1", checkpoint_id="cp_1")

        # Modify data and create another checkpoint
        task = fsm.get_task("task_1")
        task.data["counter"] = 100
        fsm.create_checkpoint("task_1", checkpoint_id="cp_2")

        # Restore from first checkpoint
        fsm.restore_checkpoint("task_1", "cp_1")

        restored_task = fsm.get_task("task_1")
        assert restored_task.data["counter"] == 0  # Should be restored to 0
        assert restored_task.current_state == TaskState.RECOVERING

    def test_restore_latest_checkpoint(self, fsm):
        """Test restoring from latest checkpoint when no ID specified"""
        fsm.create_task("task_1", data={"value": 1})
        fsm.create_checkpoint("task_1")

        task = fsm.get_task("task_1")
        task.data["value"] = 2
        fsm.create_checkpoint("task_1")

        task.data["value"] = 3

        # Restore from latest checkpoint (value should be 2)
        fsm.restore_checkpoint("task_1")

        restored_task = fsm.get_task("task_1")
        assert restored_task.data["value"] == 2

    def test_restore_nonexistent_checkpoint(self, fsm):
        """Test restoring nonexistent checkpoint raises error"""
        fsm.create_task("task_1", data={})

        with pytest.raises(ValueError, match="Checkpoint not found"):
            fsm.restore_checkpoint("task_1", "nonexistent_cp")


class TestRecoveryMechanisms:
    """Test state recovery from interruptions"""

    def test_recover_in_progress_task(self, fsm, temp_storage_dir):
        """Test recovering an in-progress task"""
        # Create task and save state
        fsm.create_task("task_1", data={"progress": 50})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.save_state("task_1")

        # Simulate interruption by creating new FSM
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        success = new_fsm.recover_task("task_1")

        assert success is True
        task = new_fsm.get_task("task_1")
        assert task is not None
        assert task.current_state == TaskState.RECOVERING
        assert task.data["progress"] == 50

    def test_recover_failed_task_with_checkpoint(self, fsm, temp_storage_dir):
        """Test recovering a failed task with checkpoints"""
        # Create task with checkpoint
        fsm.create_task("task_1", data={"attempt": 1})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.create_checkpoint("task_1")

        # Fail the task
        fsm.transition_state("task_1", TaskState.FAILED, error_message="Error occurred")
        fsm.save_state("task_1")

        # Recover task
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        success = new_fsm.recover_task("task_1")

        assert success is True
        task = new_fsm.get_task("task_1")
        assert task.current_state == TaskState.RECOVERING

    def test_recover_failed_task_exceeds_retries(self, fsm, temp_storage_dir):
        """Test recovery fails when max retries exceeded"""
        # Create task with max retries = 3
        fsm.create_task("task_1", data={}, max_retries=3)
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)

        # Fail multiple times
        for _ in range(3):
            fsm.transition_state("task_1", TaskState.FAILED)

        fsm.save_state("task_1")

        # Try to recover (should fail)
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        success = new_fsm.recover_task("task_1")

        assert success is False

    def test_recover_completed_task(self, fsm, temp_storage_dir):
        """Test recovering completed task (no recovery needed)"""
        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_1", TaskState.COMPLETED)
        fsm.save_state("task_1")

        # Try to recover
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        success = new_fsm.recover_task("task_1")

        assert success is True  # Recovery successful (no action needed)

    def test_recover_nonexistent_task(self, fsm):
        """Test recovering nonexistent task fails"""
        success = fsm.recover_task("nonexistent")
        assert success is False


class TestVersioning:
    """Test state versioning and migration"""

    def test_version_compatibility(self):
        """Test version compatibility checking"""
        v1_0_0 = StateVersion(major=1, minor=0, patch=0)
        v1_0_1 = StateVersion(major=1, minor=0, patch=1)
        v1_1_0 = StateVersion(major=1, minor=1, patch=0)
        v2_0_0 = StateVersion(major=2, minor=0, patch=0)

        # Same major version should be compatible
        assert v1_0_0.is_compatible(v1_0_1)
        assert v1_0_0.is_compatible(v1_1_0)

        # Different major version should not be compatible
        assert not v1_0_0.is_compatible(v2_0_0)

    def test_version_string_representation(self):
        """Test version string representation"""
        version = StateVersion(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

    def test_state_version_in_saved_file(self, fsm):
        """Test that version is saved with state"""
        fsm.create_task("task_1", data={})
        file_path = fsm.save_state("task_1")

        with open(file_path, 'r') as f:
            saved_data = json.load(f)

        assert "version" in saved_data
        assert saved_data["version"]["major"] == 1
        assert saved_data["version"]["minor"] == 0
        assert saved_data["version"]["patch"] == 0

    def test_load_state_with_same_version(self, fsm, temp_storage_dir):
        """Test loading state with same version"""
        fsm.create_task("task_1", data={"test": "data"})
        fsm.save_state("task_1")

        # Load with same version
        new_fsm = StateManagerFSA(storage_path=temp_storage_dir)
        task = new_fsm.load_state("task_1")

        assert task is not None
        assert task.task_id == "task_1"

    def test_auto_migration_on_load(self, fsm, temp_storage_dir):
        """Test automatic migration when loading older version"""
        # Create state with older version
        fsm.create_task("task_1", data={"test": "data"})
        file_path = fsm.save_state("task_1")

        # Manually modify version in saved file
        with open(file_path, 'r') as f:
            saved_data = json.load(f)

        saved_data["version"] = {"major": 1, "minor": 0, "patch": 0}

        with open(file_path, 'w') as f:
            json.dump(saved_data, f)

        # Load with auto migration
        task = fsm.load_state("task_1", auto_migrate=True)

        assert task is not None
        assert task.task_id == "task_1"


class TestUtilityFunctions:
    """Test utility and helper functions"""

    def test_get_all_tasks(self, fsm):
        """Test retrieving all tasks"""
        fsm.create_task("task_1", data={})
        fsm.create_task("task_2", data={})
        fsm.create_task("task_3", data={})

        all_tasks = fsm.get_all_tasks()
        assert len(all_tasks) == 3

    def test_get_all_tasks_with_filter(self, fsm):
        """Test retrieving tasks filtered by state"""
        fsm.create_task("task_1", data={})
        fsm.create_task("task_2", data={})
        fsm.create_task("task_3", data={})

        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.transition_state("task_2", TaskState.IN_PROGRESS)

        in_progress_tasks = fsm.get_all_tasks(state_filter=TaskState.IN_PROGRESS)
        assert len(in_progress_tasks) == 2

        pending_tasks = fsm.get_all_tasks(state_filter=TaskState.PENDING)
        assert len(pending_tasks) == 1

    def test_delete_task(self, fsm):
        """Test deleting a task"""
        fsm.create_task("task_1", data={})
        fsm.save_state("task_1")

        # Verify task exists
        assert fsm.get_task("task_1") is not None

        # Delete task
        success = fsm.delete_task("task_1", delete_from_disk=True)

        assert success is True
        assert fsm.get_task("task_1") is None

        # Verify file is deleted
        file_path = Path(fsm.storage_path) / "task_1.json"
        assert not file_path.exists()

    def test_get_statistics(self, fsm):
        """Test getting statistics"""
        fsm.create_task("task_1", data={})
        fsm.create_task("task_2", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        fsm.create_checkpoint("task_1")

        stats = fsm.get_statistics()

        assert stats["total_tasks"] == 2
        assert stats["state_counts"][TaskState.PENDING.value] == 1
        assert stats["state_counts"][TaskState.IN_PROGRESS.value] == 1
        assert stats["total_checkpoints"] == 1

    def test_repr(self, fsm):
        """Test string representation"""
        fsm.create_task("task_1", data={})
        repr_str = repr(fsm)

        assert "StateManagerFSA" in repr_str
        assert "tasks=1" in repr_str


class TestAutoCheckpoint:
    """Test automatic checkpointing functionality"""

    def test_auto_checkpoint_disabled(self, temp_storage_dir):
        """Test that auto-checkpoint doesn't create checkpoints when disabled"""
        config = CheckpointConfig(auto_checkpoint=False)
        fsm = StateManagerFSA(storage_path=temp_storage_dir, checkpoint_config=config)

        fsm.create_task("task_1", data={})
        fsm.transition_state("task_1", TaskState.IN_PROGRESS)

        task = fsm.get_task("task_1")
        assert len(task.checkpoints) == 0

    def test_auto_checkpoint_on_create(self, temp_storage_dir):
        """Test that auto-checkpoint saves state on task creation"""
        config = CheckpointConfig(auto_checkpoint=True)
        fsm = StateManagerFSA(storage_path=temp_storage_dir, checkpoint_config=config)

        fsm.create_task("task_1", data={"test": "data"})

        # Verify state file was created
        file_path = Path(temp_storage_dir) / "task_1.json"
        assert file_path.exists()


class TestDataStructures:
    """Test data structure conversions"""

    def test_checkpoint_to_dict(self):
        """Test checkpoint to_dict conversion"""
        checkpoint = Checkpoint(
            checkpoint_id="cp_1",
            task_id="task_1",
            state=TaskState.IN_PROGRESS,
            timestamp=123456.789,
            data={"key": "value"},
            metadata={"note": "test"}
        )

        checkpoint_dict = checkpoint.to_dict()

        assert checkpoint_dict["checkpoint_id"] == "cp_1"
        assert checkpoint_dict["task_id"] == "task_1"
        assert checkpoint_dict["state"] == TaskState.IN_PROGRESS.value
        assert checkpoint_dict["timestamp"] == 123456.789
        assert checkpoint_dict["data"] == {"key": "value"}

    def test_checkpoint_from_dict(self):
        """Test checkpoint from_dict conversion"""
        data = {
            "checkpoint_id": "cp_1",
            "task_id": "task_1",
            "state": "in_progress",
            "timestamp": 123456.789,
            "data": {"key": "value"},
            "metadata": {"note": "test"}
        }

        checkpoint = Checkpoint.from_dict(data)

        assert checkpoint.checkpoint_id == "cp_1"
        assert checkpoint.task_id == "task_1"
        assert checkpoint.state == TaskState.IN_PROGRESS
        assert checkpoint.timestamp == 123456.789
        assert checkpoint.data == {"key": "value"}

    def test_task_state_to_dict(self):
        """Test task state to_dict conversion"""
        task = TaskStateData(
            task_id="task_1",
            current_state=TaskState.IN_PROGRESS,
            data={"key": "value"},
            metadata={"priority": "high"}
        )

        task_dict = task.to_dict()

        assert task_dict["task_id"] == "task_1"
        assert task_dict["current_state"] == TaskState.IN_PROGRESS.value
        assert task_dict["data"] == {"key": "value"}
        assert task_dict["metadata"]["priority"] == "high"

    def test_task_state_from_dict(self):
        """Test task state from_dict conversion"""
        data = {
            "task_id": "task_1",
            "current_state": "in_progress",
            "data": {"key": "value"},
            "previous_state": "pending",
            "created_at": 123456.0,
            "updated_at": 123457.0,
            "checkpoints": [],
            "metadata": {"priority": "high"},
            "retry_count": 0,
            "max_retries": 3,
            "error_message": None
        }

        task = TaskStateData.from_dict(data)

        assert task.task_id == "task_1"
        assert task.current_state == TaskState.IN_PROGRESS
        assert task.previous_state == TaskState.PENDING
        assert task.data == {"key": "value"}
        assert task.metadata["priority"] == "high"

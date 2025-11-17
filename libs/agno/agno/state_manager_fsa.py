"""
State Manager FSA (Finite State Automaton)

This module provides a comprehensive state management system for task persistence
and recovery. It handles task state transitions, checkpointing, and recovery from
interruptions.

Author: Agno Team
License: MIT
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from agno.utils.log import logger


class TaskState(Enum):
    """Enumeration of possible task states in the FSA"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"  # For tasks that are temporarily paused
    RECOVERING = "recovering"  # For tasks in recovery mode


@dataclass
class Checkpoint:
    """Represents a state checkpoint with timestamp and metadata"""

    # Unique checkpoint ID
    checkpoint_id: str
    # Task ID this checkpoint belongs to
    task_id: str
    # State at the time of checkpoint
    state: TaskState
    # Timestamp when checkpoint was created (unix timestamp)
    timestamp: float
    # Checkpoint data payload
    data: Dict[str, Any]
    # Checkpoint metadata (version, notes, etc.)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Checkpoint:
        """Create checkpoint from dictionary"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            task_id=data["task_id"],
            state=TaskState(data["state"]),
            timestamp=data["timestamp"],
            data=data["data"],
            metadata=data.get("metadata")
        )


@dataclass
class TaskStateData:
    """Represents the complete state of a task"""

    # Unique task identifier
    task_id: str
    # Current state of the task
    current_state: TaskState
    # Task data payload
    data: Dict[str, Any]
    # Previous state (for state transition tracking)
    previous_state: Optional[TaskState] = None
    # When the task was created (unix timestamp)
    created_at: float = field(default_factory=time.time)
    # When the task was last updated (unix timestamp)
    updated_at: float = field(default_factory=time.time)
    # List of checkpoints for this task
    checkpoints: List[Checkpoint] = field(default_factory=list)
    # Task metadata (priority, tags, etc.)
    metadata: Optional[Dict[str, Any]] = None
    # Retry count for failed tasks
    retry_count: int = 0
    # Maximum retry attempts
    max_retries: int = 3
    # Error message if task failed
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task state to dictionary"""
        return {
            "task_id": self.task_id,
            "current_state": self.current_state.value,
            "data": self.data,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "metadata": self.metadata or {},
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskStateData:
        """Create task state from dictionary"""
        return cls(
            task_id=data["task_id"],
            current_state=TaskState(data["current_state"]),
            data=data["data"],
            previous_state=TaskState(data["previous_state"]) if data.get("previous_state") else None,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            checkpoints=[Checkpoint.from_dict(cp) for cp in data.get("checkpoints", [])],
            metadata=data.get("metadata"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message")
        )


@dataclass
class CheckpointConfig:
    """Configuration for checkpoint management"""

    # Enable automatic checkpointing
    auto_checkpoint: bool = True
    # Checkpoint interval in seconds (0 = disabled)
    checkpoint_interval: float = 300.0  # 5 minutes
    # Maximum number of checkpoints to keep per task
    max_checkpoints: int = 10
    # Enable checkpoint compression (for large state data)
    compress_checkpoints: bool = False
    # Checkpoint directory path
    checkpoint_dir: Optional[str] = None


@dataclass
class StateVersion:
    """Represents version information for state data"""

    # Major version (breaking changes)
    major: int = 1
    # Minor version (backward-compatible features)
    minor: int = 0
    # Patch version (bug fixes)
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_dict(self) -> Dict[str, int]:
        return {"major": self.major, "minor": self.minor, "patch": self.patch}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> StateVersion:
        return cls(
            major=data.get("major", 1),
            minor=data.get("minor", 0),
            patch=data.get("patch", 0)
        )

    def is_compatible(self, other: StateVersion) -> bool:
        """Check if this version is compatible with another version"""
        # Only compatible if major versions match
        return self.major == other.major


class StateManagerFSA:
    """
    State Manager FSA (Finite State Automaton)

    Manages task state persistence, transitions, checkpointing, and recovery.
    Provides a robust system for handling task state across interruptions and failures.

    Features:
    - Task state tracking (pending, in-progress, completed, failed)
    - Automatic and manual checkpointing
    - State persistence to disk (JSON format)
    - State recovery from interruptions
    - State versioning and migration
    - Configurable retry logic

    Example:
        >>> config = CheckpointConfig(auto_checkpoint=True, checkpoint_interval=60)
        >>> fsm = StateManagerFSA(storage_path="/tmp/states", checkpoint_config=config)
        >>> fsm.create_task("task_1", {"name": "Process data"})
        >>> fsm.transition_state("task_1", TaskState.IN_PROGRESS)
        >>> fsm.save_state("task_1")
    """

    # Current version of the state manager
    CURRENT_VERSION = StateVersion(major=1, minor=0, patch=0)

    # Valid state transitions (FSA rules)
    VALID_TRANSITIONS = {
        TaskState.PENDING: [TaskState.IN_PROGRESS, TaskState.SUSPENDED, TaskState.FAILED],
        TaskState.IN_PROGRESS: [TaskState.COMPLETED, TaskState.FAILED, TaskState.SUSPENDED],
        TaskState.COMPLETED: [],  # Terminal state
        TaskState.FAILED: [TaskState.PENDING, TaskState.RECOVERING],  # Can retry
        TaskState.SUSPENDED: [TaskState.IN_PROGRESS, TaskState.FAILED],
        TaskState.RECOVERING: [TaskState.IN_PROGRESS, TaskState.FAILED]
    }

    def __init__(
        self,
        storage_path: Optional[str] = None,
        checkpoint_config: Optional[CheckpointConfig] = None,
        version: Optional[StateVersion] = None
    ):
        """
        Initialize the State Manager FSA

        Args:
            storage_path: Directory path for storing state files
            checkpoint_config: Configuration for checkpoint management
            version: State version (defaults to CURRENT_VERSION)
        """
        # Set storage path (default to /tmp/agno_states)
        self.storage_path = Path(storage_path or "/tmp/agno_states")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Set checkpoint configuration
        self.checkpoint_config = checkpoint_config or CheckpointConfig()
        if self.checkpoint_config.checkpoint_dir:
            self.checkpoint_dir = Path(self.checkpoint_config.checkpoint_dir)
        else:
            self.checkpoint_dir = self.storage_path / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Set version
        self.version = version or self.CURRENT_VERSION

        # In-memory state store
        self.tasks: Dict[str, TaskStateData] = {}

        # Last checkpoint time per task
        self.last_checkpoint_time: Dict[str, float] = {}

        logger.info(f"StateManagerFSA initialized: storage={self.storage_path}, version={self.version}")

    def create_task(
        self,
        task_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> TaskStateData:
        """
        Create a new task in PENDING state

        Args:
            task_id: Unique identifier for the task
            data: Task data payload
            metadata: Optional metadata for the task
            max_retries: Maximum number of retry attempts for failed tasks

        Returns:
            TaskStateData: Created task state

        Raises:
            ValueError: If task_id already exists
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        task_state = TaskStateData(
            task_id=task_id,
            current_state=TaskState.PENDING,
            data=data,
            metadata=metadata,
            max_retries=max_retries
        )

        self.tasks[task_id] = task_state
        logger.info(f"Created task {task_id} in state {TaskState.PENDING.value}")

        # Auto-save if enabled
        if self.checkpoint_config.auto_checkpoint:
            self.save_state(task_id)

        return task_state

    def get_task(self, task_id: str) -> Optional[TaskStateData]:
        """
        Get task state by ID

        Args:
            task_id: Task identifier

        Returns:
            TaskStateData if found, None otherwise
        """
        return self.tasks.get(task_id)

    def transition_state(
        self,
        task_id: str,
        new_state: TaskState,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Transition task to a new state following FSA rules

        Args:
            task_id: Task identifier
            new_state: Target state
            error_message: Error message if transitioning to FAILED state

        Returns:
            bool: True if transition was successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
            RuntimeError: If transition is invalid
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        current_state = task.current_state

        # Check if transition is valid
        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            # Special case: allow transition to same state
            if new_state != current_state:
                raise RuntimeError(
                    f"Invalid state transition: {current_state.value} -> {new_state.value}"
                )

        # Update task state
        task.previous_state = current_state
        task.current_state = new_state
        task.updated_at = time.time()

        # Handle error message for FAILED state
        if new_state == TaskState.FAILED:
            task.error_message = error_message
            task.retry_count += 1

        logger.info(f"Task {task_id} transitioned: {current_state.value} -> {new_state.value}")

        # Auto-checkpoint if enabled and interval passed
        if self.checkpoint_config.auto_checkpoint:
            self._auto_checkpoint(task_id)

        return True

    def create_checkpoint(
        self,
        task_id: str,
        checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """
        Create a checkpoint for the current task state

        Args:
            task_id: Task identifier
            checkpoint_id: Optional checkpoint ID (auto-generated if not provided)
            metadata: Optional checkpoint metadata

        Returns:
            Checkpoint: Created checkpoint

        Raises:
            ValueError: If task doesn't exist
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Generate checkpoint ID if not provided
        if not checkpoint_id:
            checkpoint_id = f"{task_id}_cp_{int(time.time() * 1000)}"

        # Create checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            state=task.current_state,
            timestamp=time.time(),
            data=task.data.copy(),
            metadata=metadata
        )

        # Add checkpoint to task
        task.checkpoints.append(checkpoint)

        # Limit number of checkpoints
        if len(task.checkpoints) > self.checkpoint_config.max_checkpoints:
            # Remove oldest checkpoints
            task.checkpoints = task.checkpoints[-self.checkpoint_config.max_checkpoints:]

        # Update last checkpoint time
        self.last_checkpoint_time[task_id] = time.time()

        # Save checkpoint to disk
        self._save_checkpoint(checkpoint)

        logger.info(f"Created checkpoint {checkpoint_id} for task {task_id}")

        return checkpoint

    def restore_checkpoint(
        self,
        task_id: str,
        checkpoint_id: Optional[str] = None
    ) -> bool:
        """
        Restore task state from a checkpoint

        Args:
            task_id: Task identifier
            checkpoint_id: Checkpoint ID (uses latest if not provided)

        Returns:
            bool: True if restore was successful

        Raises:
            ValueError: If task or checkpoint doesn't exist
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Find checkpoint
        if checkpoint_id:
            checkpoint = next(
                (cp for cp in task.checkpoints if cp.checkpoint_id == checkpoint_id),
                None
            )
        else:
            # Use latest checkpoint
            checkpoint = task.checkpoints[-1] if task.checkpoints else None

        if not checkpoint:
            raise ValueError(f"Checkpoint not found for task {task_id}")

        # Restore state from checkpoint
        task.data = checkpoint.data.copy()
        task.previous_state = task.current_state
        task.current_state = TaskState.RECOVERING
        task.updated_at = time.time()

        logger.info(f"Restored task {task_id} from checkpoint {checkpoint.checkpoint_id}")

        return True

    def save_state(self, task_id: str) -> str:
        """
        Save task state to disk (JSON format)

        Args:
            task_id: Task identifier

        Returns:
            str: Path to saved state file

        Raises:
            ValueError: If task doesn't exist
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Prepare state data with version
        state_data = {
            "version": self.version.to_dict(),
            "task": task.to_dict(),
            "saved_at": time.time()
        }

        # Save to file
        file_path = self.storage_path / f"{task_id}.json"
        with open(file_path, 'w') as f:
            json.dump(state_data, f, indent=2)

        logger.info(f"Saved state for task {task_id} to {file_path}")

        return str(file_path)

    def load_state(self, task_id: str, auto_migrate: bool = True) -> Optional[TaskStateData]:
        """
        Load task state from disk

        Args:
            task_id: Task identifier
            auto_migrate: Automatically migrate state if version mismatch

        Returns:
            TaskStateData if loaded successfully, None otherwise
        """
        file_path = self.storage_path / f"{task_id}.json"

        if not file_path.exists():
            logger.warning(f"State file not found for task {task_id}")
            return None

        try:
            with open(file_path, 'r') as f:
                state_data = json.load(f)

            # Check version
            saved_version = StateVersion.from_dict(state_data.get("version", {}))

            if not saved_version.is_compatible(self.version):
                logger.warning(
                    f"Version mismatch: saved={saved_version}, current={self.version}"
                )
                if auto_migrate:
                    state_data = self._migrate_state(state_data, saved_version)
                else:
                    raise RuntimeError(
                        f"Incompatible state version: {saved_version} vs {self.version}"
                    )

            # Load task state
            task = TaskStateData.from_dict(state_data["task"])
            self.tasks[task_id] = task

            logger.info(f"Loaded state for task {task_id} from {file_path}")

            return task

        except Exception as e:
            logger.error(f"Failed to load state for task {task_id}: {e}")
            return None

    def recover_task(self, task_id: str) -> bool:
        """
        Recover a task from saved state (handles interruptions)

        Args:
            task_id: Task identifier

        Returns:
            bool: True if recovery was successful
        """
        # Try to load state from disk
        task = self.load_state(task_id)

        if not task:
            logger.error(f"Cannot recover task {task_id}: state not found")
            return False

        # Check if task needs recovery
        if task.current_state in [TaskState.COMPLETED]:
            logger.info(f"Task {task_id} already completed, no recovery needed")
            return True

        if task.current_state == TaskState.FAILED:
            # Check retry count
            if task.retry_count >= task.max_retries:
                logger.error(
                    f"Task {task_id} exceeded max retries ({task.max_retries})"
                )
                return False

            # Attempt recovery from latest checkpoint
            if task.checkpoints:
                self.restore_checkpoint(task_id)
                logger.info(f"Recovered task {task_id} from checkpoint")
                return True

        # For in-progress or suspended tasks, transition to recovering state
        if task.current_state in [TaskState.IN_PROGRESS, TaskState.SUSPENDED]:
            task.current_state = TaskState.RECOVERING
            task.updated_at = time.time()
            logger.info(f"Task {task_id} set to RECOVERING state")
            return True

        return False

    def get_all_tasks(self, state_filter: Optional[TaskState] = None) -> List[TaskStateData]:
        """
        Get all tasks, optionally filtered by state

        Args:
            state_filter: Optional state to filter by

        Returns:
            List[TaskStateData]: List of tasks
        """
        tasks = list(self.tasks.values())

        if state_filter:
            tasks = [t for t in tasks if t.current_state == state_filter]

        return tasks

    def delete_task(self, task_id: str, delete_from_disk: bool = True) -> bool:
        """
        Delete a task from memory and optionally from disk

        Args:
            task_id: Task identifier
            delete_from_disk: Whether to delete state file from disk

        Returns:
            bool: True if deletion was successful
        """
        # Remove from memory
        if task_id in self.tasks:
            del self.tasks[task_id]

        # Remove from disk
        if delete_from_disk:
            file_path = self.storage_path / f"{task_id}.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted state file for task {task_id}")

        # Remove checkpoint time
        if task_id in self.last_checkpoint_time:
            del self.last_checkpoint_time[task_id]

        logger.info(f"Deleted task {task_id}")

        return True

    def _auto_checkpoint(self, task_id: str) -> None:
        """
        Automatically create checkpoint if interval has passed

        Args:
            task_id: Task identifier
        """
        if self.checkpoint_config.checkpoint_interval <= 0:
            return

        last_checkpoint = self.last_checkpoint_time.get(task_id, 0)
        now = time.time()

        if now - last_checkpoint >= self.checkpoint_config.checkpoint_interval:
            self.create_checkpoint(task_id)

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Save checkpoint to disk

        Args:
            checkpoint: Checkpoint to save
        """
        file_path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"

        with open(file_path, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def _migrate_state(
        self,
        state_data: Dict[str, Any],
        from_version: StateVersion
    ) -> Dict[str, Any]:
        """
        Migrate state data from older version to current version

        Args:
            state_data: State data to migrate
            from_version: Source version

        Returns:
            Dict[str, Any]: Migrated state data
        """
        logger.info(f"Migrating state from version {from_version} to {self.version}")

        # Example migration logic (add specific migrations as needed)
        # For now, just update the version
        state_data["version"] = self.version.to_dict()

        # Add any version-specific migrations here
        # if from_version.major == 1 and from_version.minor == 0:
        #     # Migrate from 1.0.x to 1.1.x
        #     pass

        return state_data

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current state manager

        Returns:
            Dict[str, Any]: Statistics including task counts by state
        """
        total_tasks = len(self.tasks)

        state_counts = {state.value: 0 for state in TaskState}
        for task in self.tasks.values():
            state_counts[task.current_state.value] += 1

        total_checkpoints = sum(len(task.checkpoints) for task in self.tasks.values())

        return {
            "total_tasks": total_tasks,
            "state_counts": state_counts,
            "total_checkpoints": total_checkpoints,
            "storage_path": str(self.storage_path),
            "version": str(self.version)
        }

    def __repr__(self) -> str:
        return (
            f"StateManagerFSA(tasks={len(self.tasks)}, "
            f"storage_path={self.storage_path}, "
            f"version={self.version})"
        )

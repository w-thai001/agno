"""Queue Manager FSA - Finite State Automaton for task queue management."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from collections import deque

class QueueState(Enum):
    """Queue task states."""
    IDLE, QUEUED, PROCESSING, COMPLETED, FAILED, PAUSED = range(6)

@dataclass
class QueueTask:
    """Represents a task in the queue."""
    task_id: str
    state: QueueState = QueueState.IDLE
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class QueueManager:
    """FSA-based queue manager for task processing."""
    VALID_TRANSITIONS: Dict[QueueState, List[QueueState]] = {
        QueueState.IDLE: [QueueState.QUEUED],
        QueueState.QUEUED: [QueueState.PROCESSING, QueueState.PAUSED],
        QueueState.PROCESSING: [QueueState.COMPLETED, QueueState.FAILED, QueueState.PAUSED],
        QueueState.PAUSED: [QueueState.QUEUED],
        QueueState.COMPLETED: [],
        QueueState.FAILED: [QueueState.QUEUED],
    }

    def __init__(self):
        self.tasks: Dict[str, QueueTask] = {}
        self.queue: deque[str] = deque()
        self.handlers: Dict[QueueState, Callable] = {}

    def add_task(self, task: QueueTask) -> bool:
        """Add task and transition to QUEUED state."""
        if task.task_id in self.tasks:
            return False
        self.tasks[task.task_id] = task
        return self.transition(task.task_id, QueueState.QUEUED)

    def transition(self, task_id: str, new_state: QueueState) -> bool:
        """Validate and execute state transition."""
        task = self.tasks.get(task_id)
        if not task or new_state not in self.VALID_TRANSITIONS.get(task.state, []):
            return False
        task.state, task.updated_at = new_state, datetime.now()
        if new_state == QueueState.QUEUED and task_id not in self.queue:
            self.queue.append(task_id)
        elif new_state in [QueueState.COMPLETED, QueueState.FAILED] and task_id in self.queue:
            self.queue.remove(task_id)
        if new_state in self.handlers:
            self.handlers[new_state](task)
        return True

    def process_next(self) -> Optional[QueueTask]:
        """Process next task in queue."""
        if not self.queue:
            return None
        task_id = self.queue.popleft()
        self.transition(task_id, QueueState.PROCESSING)
        return self.tasks[task_id]

    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """Mark task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].result = result
            return self.transition(task_id, QueueState.COMPLETED)
        return False

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed."""
        if task_id in self.tasks:
            self.tasks[task_id].error = error
            return self.transition(task_id, QueueState.FAILED)
        return False

    def get_state(self, task_id: str) -> Optional[QueueState]:
        """Get current state of a task."""
        return self.tasks[task_id].state if task_id in self.tasks else None

    def register_handler(self, state: QueueState, handler: Callable) -> None:
        """Register callback for state transitions."""
        self.handlers[state] = handler

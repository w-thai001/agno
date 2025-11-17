"""
Integration tests for OrchestratorFSA.

Tests cover:
- Basic orchestration scenarios
- Dependency management
- Parallel execution
- Error handling and recovery
- State management
- Progress monitoring
"""

import pytest
from typing import Any, Dict, List
from datetime import datetime

from agno.agent import Agent
from agno.storage.json import JsonStorage
from agno.workflow.orchestrator_fsa import (
    ExecutionStrategy,
    FSATask,
    OrchestratorConfig,
    OrchestratorFSA,
    OrchestratorState,
    RecoveryStrategy,
)
from agno.workflow.fsa import (
    FSA,
    FSAConfig,
    FSAState,
    StateTransition,
)


# Mock FSA for testing
class TestFSAState(str, FSAState):
    """Test FSA states."""
    INIT = "init"
    PROCESSING = "processing"
    DONE = "done"


class SimpleFSA(FSA):
    """Simple FSA for testing."""

    def __init__(self, name: str, result_value: Any = None, should_fail: bool = False):
        self.result_value = result_value or f"Result from {name}"
        self.should_fail = should_fail

        config = FSAConfig(
            name=name,
            initial_state=TestFSAState.INIT,
            final_states=[TestFSAState.DONE],
            transitions=[
                StateTransition(
                    from_state=TestFSAState.INIT,
                    to_state=TestFSAState.PROCESSING,
                    description="Start processing"
                ),
                StateTransition(
                    from_state=TestFSAState.PROCESSING,
                    to_state=TestFSAState.DONE,
                    description="Complete processing"
                )
            ]
        )

        super().__init__(config=config, session_state={})

    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute simple FSA."""
        if self.should_fail:
            raise RuntimeError(f"FSA {self.config.name} intentionally failed")

        # Simulate state transitions
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        # Merge kwargs with result
        result = {"output": self.result_value}
        result.update(kwargs)

        return result


# Fixtures
@pytest.fixture
def tmp_storage(tmp_path):
    """Create temporary JSON storage."""
    return JsonStorage(dir_path=tmp_path)


@pytest.fixture
def simple_orchestrator(tmp_storage):
    """Create a simple orchestrator with basic tasks."""
    tasks = [
        FSATask(
            name="task1",
            fsa=SimpleFSA("task1", result_value="Task 1 output"),
            dependencies=[],
            output_mapping={"output": "task1_output"}
        ),
        FSATask(
            name="task2",
            fsa=SimpleFSA("task2", result_value="Task 2 output"),
            dependencies=["task1"],
            input_mapping={"task1_output": "input_data"},
            output_mapping={"output": "task2_output"}
        ),
        FSATask(
            name="task3",
            fsa=SimpleFSA("task3", result_value="Task 3 output"),
            dependencies=["task2"],
            input_mapping={"task2_output": "input_data"}
        )
    ]

    config = OrchestratorConfig(
        execution_strategy=ExecutionStrategy.SEQUENTIAL,
        recovery_strategy=RecoveryStrategy.FAIL_FAST,
        enable_monitoring=False
    )

    return OrchestratorFSA(
        tasks=tasks,
        config=config,
        storage=tmp_storage,
        name="TestOrchestrator"
    )


@pytest.fixture
def parallel_orchestrator(tmp_storage):
    """Create orchestrator with parallel-capable tasks."""
    tasks = [
        FSATask(
            name="parallel1",
            fsa=SimpleFSA("parallel1", result_value="P1"),
            dependencies=[],
            can_run_parallel=True
        ),
        FSATask(
            name="parallel2",
            fsa=SimpleFSA("parallel2", result_value="P2"),
            dependencies=[],
            can_run_parallel=True
        ),
        FSATask(
            name="parallel3",
            fsa=SimpleFSA("parallel3", result_value="P3"),
            dependencies=[],
            can_run_parallel=True
        ),
        FSATask(
            name="final",
            fsa=SimpleFSA("final", result_value="Final"),
            dependencies=["parallel1", "parallel2", "parallel3"]
        )
    ]

    config = OrchestratorConfig(
        execution_strategy=ExecutionStrategy.PARALLEL,
        max_parallel_tasks=3,
        enable_monitoring=False
    )

    return OrchestratorFSA(
        tasks=tasks,
        config=config,
        storage=tmp_storage,
        name="ParallelOrchestrator"
    )


# Tests
class TestOrchestratorFSABasics:
    """Test basic orchestrator functionality."""

    def test_initialization(self, simple_orchestrator):
        """Test orchestrator initialization."""
        assert simple_orchestrator is not None
        assert len(simple_orchestrator.tasks) == 3
        assert simple_orchestrator.context.current_state == OrchestratorState.IDLE

    def test_task_addition(self, tmp_storage):
        """Test adding tasks to orchestrator."""
        orchestrator = OrchestratorFSA(storage=tmp_storage, name="TestAdd")

        task = FSATask(
            name="new_task",
            fsa=SimpleFSA("new_task")
        )

        orchestrator.add_task(task)
        assert len(orchestrator.tasks) == 1
        assert orchestrator.tasks[0].name == "new_task"


class TestDependencyManagement:
    """Test dependency resolution and validation."""

    def test_valid_dependencies(self, simple_orchestrator):
        """Test validation of valid dependencies."""
        assert simple_orchestrator.validate_tasks() is True

    def test_invalid_dependency(self, tmp_storage):
        """Test detection of invalid dependencies."""
        tasks = [
            FSATask(
                name="task1",
                fsa=SimpleFSA("task1"),
                dependencies=["nonexistent_task"]
            )
        ]

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            storage=tmp_storage,
            name="InvalidDeps"
        )

        assert orchestrator.validate_tasks() is False

    def test_circular_dependency_detection(self, tmp_storage):
        """Test detection of circular dependencies."""
        tasks = [
            FSATask(
                name="task1",
                fsa=SimpleFSA("task1"),
                dependencies=["task2"]
            ),
            FSATask(
                name="task2",
                fsa=SimpleFSA("task2"),
                dependencies=["task1"]
            )
        ]

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            storage=tmp_storage,
            name="CircularDeps"
        )

        assert orchestrator.validate_tasks() is False

    def test_execution_plan_creation(self, simple_orchestrator):
        """Test execution plan creation."""
        plan = simple_orchestrator.create_execution_plan()

        # Should have 3 batches (sequential execution)
        assert len(plan) == 3
        assert plan[0] == ["task1"]
        assert plan[1] == ["task2"]
        assert plan[2] == ["task3"]

    def test_parallel_execution_plan(self, parallel_orchestrator):
        """Test execution plan with parallel tasks."""
        plan = parallel_orchestrator.create_execution_plan()

        # Should have 2 batches: parallel tasks, then final
        assert len(plan) == 2
        assert set(plan[0]) == {"parallel1", "parallel2", "parallel3"}
        assert plan[1] == ["final"]


class TestOrchestrationExecution:
    """Test orchestration execution scenarios."""

    def test_sequential_execution(self, simple_orchestrator):
        """Test sequential task execution."""
        responses = list(simple_orchestrator.run())

        # Check that orchestration completed
        assert simple_orchestrator.context.current_state == OrchestratorState.COMPLETED
        assert len(simple_orchestrator.completed_tasks) == 3
        assert len(simple_orchestrator.failed_tasks) == 0

        # Verify all tasks completed
        for task in simple_orchestrator.tasks:
            assert task.status == "completed"
            assert task.result is not None

    def test_parallel_execution(self, parallel_orchestrator):
        """Test parallel task execution."""
        responses = list(parallel_orchestrator.run())

        # Check completion
        assert parallel_orchestrator.context.current_state == OrchestratorState.COMPLETED
        assert len(parallel_orchestrator.completed_tasks) == 4
        assert len(parallel_orchestrator.failed_tasks) == 0

    def test_data_flow(self, simple_orchestrator):
        """Test data flow between tasks."""
        list(simple_orchestrator.run())

        # Check that data was passed through mappings
        assert "task1_output" in simple_orchestrator.task_outputs.get("task1", {})
        assert "task2_output" in simple_orchestrator.task_outputs.get("task2", {})

        # Verify task2 received input from task1
        task2_result = simple_orchestrator.tasks[1].result
        assert "input_data" in task2_result
        assert task2_result["input_data"] == "Task 1 output"


class TestErrorHandling:
    """Test error handling and recovery strategies."""

    def test_fail_fast_strategy(self, tmp_storage):
        """Test fail-fast error handling."""
        tasks = [
            FSATask(
                name="task1",
                fsa=SimpleFSA("task1", should_fail=True)
            ),
            FSATask(
                name="task2",
                fsa=SimpleFSA("task2"),
                dependencies=["task1"]
            )
        ]

        config = OrchestratorConfig(
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            enable_monitoring=False
        )

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            config=config,
            storage=tmp_storage,
            name="FailFast"
        )

        list(orchestrator.run())

        # Should stop at error state
        assert orchestrator.context.current_state == OrchestratorState.ERROR
        assert len(orchestrator.failed_tasks) > 0

    def test_retry_strategy(self, tmp_storage):
        """Test retry error handling."""
        # Create a task that fails first time but succeeds on retry
        class RetryableFSA(SimpleFSA):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.attempt = 0

            def run(self, **kwargs):
                self.attempt += 1
                if self.attempt == 1:
                    raise RuntimeError("First attempt failed")
                return super().run(**kwargs)

        tasks = [
            FSATask(
                name="task1",
                fsa=RetryableFSA("task1"),
                max_retries=2
            )
        ]

        config = OrchestratorConfig(
            recovery_strategy=RecoveryStrategy.RETRY,
            enable_monitoring=False
        )

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            config=config,
            storage=tmp_storage,
            name="Retry"
        )

        list(orchestrator.run())

        # Should eventually succeed
        assert orchestrator.tasks[0].retry_count > 0

    def test_continue_strategy(self, tmp_storage):
        """Test continue-on-error strategy."""
        tasks = [
            FSATask(
                name="task1",
                fsa=SimpleFSA("task1", should_fail=True)
            ),
            FSATask(
                name="task2",
                fsa=SimpleFSA("task2"),
                dependencies=[]  # No dependency on task1
            )
        ]

        config = OrchestratorConfig(
            recovery_strategy=RecoveryStrategy.CONTINUE,
            enable_monitoring=False
        )

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            config=config,
            storage=tmp_storage,
            name="Continue"
        )

        list(orchestrator.run())

        # Task2 should still complete even though task1 failed
        assert orchestrator.tasks[1].status == "completed"


class TestStateManagement:
    """Test state management and transitions."""

    def test_state_transitions(self, simple_orchestrator):
        """Test FSA state transitions during execution."""
        # Track states visited
        states_visited = []

        for response in simple_orchestrator.run():
            current_state = simple_orchestrator.context.current_state
            if current_state not in states_visited:
                states_visited.append(current_state)

        # Should visit key states
        assert OrchestratorState.IDLE in states_visited
        assert OrchestratorState.VALIDATING in states_visited
        assert OrchestratorState.PLANNING in states_visited
        assert OrchestratorState.EXECUTING in states_visited
        assert OrchestratorState.COMPLETED in states_visited

    def test_history_tracking(self, simple_orchestrator):
        """Test state transition history."""
        list(simple_orchestrator.run())

        # Check history was recorded
        assert len(simple_orchestrator.context.history) > 0

        # Verify history entries have required fields
        for entry in simple_orchestrator.context.history:
            assert "from_state" in entry
            assert "to_state" in entry
            assert "timestamp" in entry
            assert "success" in entry

    def test_progress_tracking(self, simple_orchestrator):
        """Test progress information."""
        list(simple_orchestrator.run())

        progress = simple_orchestrator.get_progress()

        assert progress["fsa_name"] == "orchestrator"
        assert progress["current_state"] == OrchestratorState.COMPLETED.value
        assert progress["is_complete"] is True
        assert progress["transition_count"] > 0


class TestProgressMonitoring:
    """Test progress monitoring and callbacks."""

    def test_progress_callback(self, tmp_storage):
        """Test progress callback invocation."""
        progress_updates = []

        def progress_callback(progress: Dict[str, Any]):
            progress_updates.append(progress.copy())

        tasks = [
            FSATask(name="task1", fsa=SimpleFSA("task1")),
            FSATask(name="task2", fsa=SimpleFSA("task2"), dependencies=["task1"])
        ]

        config = OrchestratorConfig(
            enable_monitoring=True
        )

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            config=config,
            storage=tmp_storage,
            name="Monitored",
            progress_callback=progress_callback
        )

        list(orchestrator.run())

        # Should have received progress updates
        assert len(progress_updates) > 0

        # Verify progress data structure
        for update in progress_updates:
            assert "current_state" in update
            assert "total_tasks" in update
            assert "completed_tasks" in update
            assert "completion_percentage" in update


class TestComplexScenarios:
    """Test complex orchestration scenarios."""

    def test_diamond_dependency(self, tmp_storage):
        """Test diamond-shaped dependency graph."""
        tasks = [
            FSATask(name="start", fsa=SimpleFSA("start")),
            FSATask(name="branch1", fsa=SimpleFSA("branch1"), dependencies=["start"]),
            FSATask(name="branch2", fsa=SimpleFSA("branch2"), dependencies=["start"]),
            FSATask(name="merge", fsa=SimpleFSA("merge"), dependencies=["branch1", "branch2"])
        ]

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            storage=tmp_storage,
            name="Diamond"
        )

        list(orchestrator.run())

        assert orchestrator.context.current_state == OrchestratorState.COMPLETED
        assert len(orchestrator.completed_tasks) == 4

    def test_multi_level_dependencies(self, tmp_storage):
        """Test multiple levels of dependencies."""
        tasks = [
            FSATask(name="l0", fsa=SimpleFSA("l0")),
            FSATask(name="l1a", fsa=SimpleFSA("l1a"), dependencies=["l0"]),
            FSATask(name="l1b", fsa=SimpleFSA("l1b"), dependencies=["l0"]),
            FSATask(name="l2", fsa=SimpleFSA("l2"), dependencies=["l1a", "l1b"]),
            FSATask(name="l3", fsa=SimpleFSA("l3"), dependencies=["l2"])
        ]

        config = OrchestratorConfig(
            execution_strategy=ExecutionStrategy.ADAPTIVE
        )

        orchestrator = OrchestratorFSA(
            tasks=tasks,
            config=config,
            storage=tmp_storage,
            name="MultiLevel"
        )

        list(orchestrator.run())

        assert orchestrator.context.current_state == OrchestratorState.COMPLETED
        assert len(orchestrator.completed_tasks) == 5

    def test_empty_task_list(self, tmp_storage):
        """Test orchestrator with no tasks."""
        orchestrator = OrchestratorFSA(
            tasks=[],
            storage=tmp_storage,
            name="Empty"
        )

        list(orchestrator.run())

        # Should complete successfully even with no tasks
        assert orchestrator.context.current_state == OrchestratorState.COMPLETED
        assert len(orchestrator.completed_tasks) == 0


class TestConfiguration:
    """Test configuration options."""

    def test_custom_config(self, tmp_storage):
        """Test custom orchestrator configuration."""
        config = OrchestratorConfig(
            execution_strategy=ExecutionStrategy.PARALLEL,
            recovery_strategy=RecoveryStrategy.RETRY,
            max_parallel_tasks=2,
            enable_monitoring=True,
            enable_checkpointing=True,
            task_timeout_seconds=60
        )

        orchestrator = OrchestratorFSA(
            tasks=[],
            config=config,
            storage=tmp_storage,
            name="CustomConfig"
        )

        assert orchestrator.orchestrator_config.execution_strategy == ExecutionStrategy.PARALLEL
        assert orchestrator.orchestrator_config.max_parallel_tasks == 2
        assert orchestrator.orchestrator_config.enable_monitoring is True

    def test_execution_strategies(self, tmp_storage):
        """Test different execution strategies."""
        tasks = [
            FSATask(name="t1", fsa=SimpleFSA("t1")),
            FSATask(name="t2", fsa=SimpleFSA("t2")),
            FSATask(name="t3", fsa=SimpleFSA("t3"))
        ]

        # Test SEQUENTIAL
        config_seq = OrchestratorConfig(execution_strategy=ExecutionStrategy.SEQUENTIAL)
        orch_seq = OrchestratorFSA(tasks=tasks, config=config_seq, storage=tmp_storage, name="Seq")
        plan_seq = orch_seq.create_execution_plan()
        assert all(len(batch) == 1 for batch in plan_seq)

        # Test PARALLEL
        tasks_parallel = [
            FSATask(name="t1", fsa=SimpleFSA("t1"), can_run_parallel=True),
            FSATask(name="t2", fsa=SimpleFSA("t2"), can_run_parallel=True),
            FSATask(name="t3", fsa=SimpleFSA("t3"), can_run_parallel=True)
        ]
        config_par = OrchestratorConfig(execution_strategy=ExecutionStrategy.PARALLEL)
        orch_par = OrchestratorFSA(tasks=tasks_parallel, config=config_par, storage=tmp_storage, name="Par")
        plan_par = orch_par.create_execution_plan()
        assert len(plan_par[0]) == 3  # All in one batch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

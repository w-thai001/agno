"""
Comprehensive tests for Meta-FSA Orchestrator.

Tests cover:
- Basic FSA execution
- Dependency resolution
- Parallel execution
- Error handling and retries
- Conditional execution
- Timeout management
- State management
"""

import asyncio
import pytest
from typing import Any

from agno.fsa.orchestrator import (
    FSA,
    FSAContext,
    FSAExecutor,
    FSAOrchestrator,
    FSAResult,
    FSAStatus,
)


# Test Executors
# ==============

class SimpleExecutor(FSAExecutor):
    """Simple executor that returns a value."""

    def __init__(self, value: Any = "test"):
        self.value = value

    async def execute(self, context: FSAContext) -> Any:
        return self.value


class ContextWriterExecutor(FSAExecutor):
    """Executor that writes to context."""

    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value

    async def execute(self, context: FSAContext) -> Any:
        context.set(self.key, self.value)
        return self.value


class ContextReaderExecutor(FSAExecutor):
    """Executor that reads from context."""

    def __init__(self, key: str):
        self.key = key

    async def execute(self, context: FSAContext) -> Any:
        return context.get(self.key)


class DelayExecutor(FSAExecutor):
    """Executor with configurable delay."""

    def __init__(self, delay: float, value: Any = "done"):
        self.delay = delay
        self.value = value

    async def execute(self, context: FSAContext) -> Any:
        await asyncio.sleep(self.delay)
        return self.value


class FailingExecutor(FSAExecutor):
    """Executor that always fails."""

    async def execute(self, context: FSAContext) -> Any:
        raise Exception("Simulated failure")


class ConditionalFailExecutor(FSAExecutor):
    """Executor that fails N times then succeeds."""

    def __init__(self, fail_count: int):
        self.fail_count = fail_count
        self.attempts = 0

    async def execute(self, context: FSAContext) -> Any:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise Exception(f"Attempt {self.attempts} failed")
        return {"success": True, "attempts": self.attempts}


# Tests
# =====

class TestFSAContext:
    """Test FSAContext functionality."""

    def test_set_and_get(self):
        """Test setting and getting values."""
        ctx = FSAContext()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"

    def test_get_default(self):
        """Test getting with default value."""
        ctx = FSAContext()
        assert ctx.get("nonexistent", "default") == "default"

    def test_has(self):
        """Test checking key existence."""
        ctx = FSAContext()
        assert not ctx.has("key")
        ctx.set("key", "value")
        assert ctx.has("key")

    def test_update(self):
        """Test updating multiple values."""
        ctx = FSAContext()
        ctx.update({"a": 1, "b": 2})
        assert ctx.get("a") == 1
        assert ctx.get("b") == 2

    def test_history(self):
        """Test history tracking."""
        ctx = FSAContext()
        ctx.add_history("fsa1", FSAStatus.COMPLETED, result="success")
        ctx.add_history("fsa2", FSAStatus.FAILED, error="test error")

        assert len(ctx.history) == 2
        assert ctx.history[0]["fsa_id"] == "fsa1"
        assert ctx.history[0]["status"] == "completed"
        assert ctx.history[1]["error"] == "test error"


class TestFSAResult:
    """Test FSAResult functionality."""

    def test_duration(self):
        """Test duration calculation."""
        result = FSAResult(
            fsa_id="test",
            status=FSAStatus.COMPLETED,
            start_time=1.0,
            end_time=3.5,
        )
        assert result.duration == 2.5

    def test_success(self):
        """Test success property."""
        result1 = FSAResult(fsa_id="test", status=FSAStatus.COMPLETED)
        result2 = FSAResult(fsa_id="test", status=FSAStatus.FAILED)

        assert result1.success is True
        assert result2.success is False

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = FSAResult(
            fsa_id="test",
            status=FSAStatus.COMPLETED,
            output="result",
            start_time=1.0,
            end_time=2.0,
        )
        d = result.to_dict()

        assert d["fsa_id"] == "test"
        assert d["status"] == "completed"
        assert d["output"] == "result"
        assert d["duration"] == 1.0


class TestFSA:
    """Test FSA configuration."""

    def test_creation(self):
        """Test FSA creation."""
        fsa = FSA(
            id="test",
            name="Test FSA",
            executor=SimpleExecutor(),
        )
        assert fsa.id == "test"
        assert fsa.name == "Test FSA"
        assert fsa.max_retries == 0
        assert fsa.priority == 0

    def test_validation(self):
        """Test FSA validation."""
        with pytest.raises(ValueError):
            FSA(id="", name="Test", executor=SimpleExecutor())

        with pytest.raises(ValueError):
            FSA(id="test", name="", executor=SimpleExecutor())

        with pytest.raises(ValueError):
            FSA(id="test", name="Test", executor=SimpleExecutor(), max_retries=-1)


@pytest.mark.asyncio
class TestFSAOrchestrator:
    """Test FSAOrchestrator functionality."""

    async def test_single_fsa(self):
        """Test executing a single FSA."""
        orchestrator = FSAOrchestrator()
        fsa = FSA(id="test", name="Test", executor=SimpleExecutor("result"))
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute()

        assert len(results) == 1
        assert results["test"].status == FSAStatus.COMPLETED
        assert results["test"].output == "result"

    async def test_sequential_execution(self):
        """Test sequential execution with dependencies."""
        orchestrator = FSAOrchestrator()

        fsa1 = FSA(
            id="first",
            name="First",
            executor=ContextWriterExecutor("value", 42),
        )

        fsa2 = FSA(
            id="second",
            name="Second",
            executor=ContextReaderExecutor("value"),
            dependencies=["first"],
        )

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)

        results = await orchestrator.execute()

        assert results["first"].status == FSAStatus.COMPLETED
        assert results["second"].status == FSAStatus.COMPLETED
        assert results["second"].output == 42

    async def test_parallel_execution(self):
        """Test parallel execution of independent FSAs."""
        orchestrator = FSAOrchestrator()

        # Three FSAs that each take 0.1s
        for i in range(3):
            fsa = FSA(
                id=f"parallel_{i}",
                name=f"Parallel {i}",
                executor=DelayExecutor(0.1, i),
            )
            orchestrator.add_fsa(fsa)

        start = asyncio.get_event_loop().time()
        results = await orchestrator.execute()
        duration = asyncio.get_event_loop().time() - start

        # Should complete in ~0.1s (parallel) not ~0.3s (sequential)
        assert duration < 0.2
        assert len(results) == 3
        assert all(r.status == FSAStatus.COMPLETED for r in results.values())

    async def test_dependency_validation(self):
        """Test dependency validation."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(
            id="test",
            name="Test",
            executor=SimpleExecutor(),
            dependencies=["nonexistent"],
        )
        orchestrator.add_fsa(fsa)

        with pytest.raises(ValueError, match="non-existent"):
            await orchestrator.execute()

    async def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        orchestrator = FSAOrchestrator()

        fsa1 = FSA(
            id="a",
            name="A",
            executor=SimpleExecutor(),
            dependencies=["b"],
        )

        fsa2 = FSA(
            id="b",
            name="B",
            executor=SimpleExecutor(),
            dependencies=["a"],
        )

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)

        with pytest.raises(ValueError, match="Circular dependency"):
            await orchestrator.execute()

    async def test_retry_logic(self):
        """Test retry logic on failures."""
        orchestrator = FSAOrchestrator()

        executor = ConditionalFailExecutor(fail_count=2)
        fsa = FSA(
            id="test",
            name="Test",
            executor=executor,
            max_retries=3,
            retry_delay=0.01,
        )
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute()

        assert results["test"].status == FSAStatus.COMPLETED
        assert executor.attempts == 3

    async def test_max_retries_exhausted(self):
        """Test failure when max retries exhausted."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(
            id="test",
            name="Test",
            executor=FailingExecutor(),
            max_retries=2,
            retry_delay=0.01,
        )
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute()

        assert results["test"].status == FSAStatus.FAILED
        assert "Simulated failure" in results["test"].error

    async def test_timeout(self):
        """Test FSA timeout."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(
            id="test",
            name="Test",
            executor=DelayExecutor(1.0),
            timeout=0.1,
        )
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute()

        assert results["test"].status == FSAStatus.FAILED
        assert "Timeout" in results["test"].error

    async def test_conditional_execution(self):
        """Test conditional FSA execution."""
        orchestrator = FSAOrchestrator()

        fsa1 = FSA(
            id="always",
            name="Always Run",
            executor=SimpleExecutor("always"),
            condition=lambda ctx: True,
        )

        fsa2 = FSA(
            id="never",
            name="Never Run",
            executor=SimpleExecutor("never"),
            condition=lambda ctx: False,
        )

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)

        results = await orchestrator.execute()

        assert results["always"].status == FSAStatus.COMPLETED
        assert results["never"].status == FSAStatus.SKIPPED

    async def test_validation_skip(self):
        """Test skipping FSA when validation fails."""

        class ValidatingExecutor(FSAExecutor):
            def validate(self, context: FSAContext) -> bool:
                return context.has("required_key")

            async def execute(self, context: FSAContext) -> Any:
                return "executed"

        orchestrator = FSAOrchestrator()
        fsa = FSA(id="test", name="Test", executor=ValidatingExecutor())
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute()

        assert results["test"].status == FSAStatus.SKIPPED

    async def test_stop_on_failure(self):
        """Test stopping execution on failure."""
        orchestrator = FSAOrchestrator()

        fsa1 = FSA(id="fail", name="Fail", executor=FailingExecutor())
        fsa2 = FSA(id="after", name="After", executor=SimpleExecutor(), dependencies=["fail"])

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)

        results = await orchestrator.execute(stop_on_failure=True)

        assert results["fail"].status == FSAStatus.FAILED
        assert results["after"].status == FSAStatus.CANCELLED

    async def test_priority_ordering(self):
        """Test FSA execution priority."""
        orchestrator = FSAOrchestrator()
        execution_order = []

        class OrderTrackingExecutor(FSAExecutor):
            def __init__(self, name: str):
                self.name = name

            async def execute(self, context: FSAContext) -> Any:
                execution_order.append(self.name)
                return self.name

        # Create FSAs with different priorities
        fsa1 = FSA(id="low", name="Low", executor=OrderTrackingExecutor("low"), priority=1)
        fsa2 = FSA(id="high", name="High", executor=OrderTrackingExecutor("high"), priority=10)
        fsa3 = FSA(id="medium", name="Medium", executor=OrderTrackingExecutor("medium"), priority=5)

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)
        orchestrator.add_fsa(fsa3)

        await orchestrator.execute()

        # Higher priority should execute first
        assert execution_order[0] == "high"
        assert execution_order[1] == "medium"
        assert execution_order[2] == "low"

    async def test_initial_context(self):
        """Test providing initial context."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(id="test", name="Test", executor=ContextReaderExecutor("initial_value"))
        orchestrator.add_fsa(fsa)

        results = await orchestrator.execute(initial_context={"initial_value": 123})

        assert results["test"].output == 123

    async def test_progress_callback(self):
        """Test progress callback."""
        callbacks = []

        def callback(fsa_id: str, status: FSAStatus):
            callbacks.append((fsa_id, status))

        orchestrator = FSAOrchestrator()
        orchestrator.set_progress_callback(callback)

        fsa = FSA(id="test", name="Test", executor=SimpleExecutor())
        orchestrator.add_fsa(fsa)

        await orchestrator.execute()

        # Should have callbacks for RUNNING and COMPLETED
        assert len(callbacks) >= 2
        assert any(status == FSAStatus.RUNNING for _, status in callbacks)
        assert any(status == FSAStatus.COMPLETED for _, status in callbacks)

    async def test_get_output(self):
        """Test getting FSA output."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(id="test", name="Test", executor=SimpleExecutor("result"))
        orchestrator.add_fsa(fsa)

        await orchestrator.execute()

        assert orchestrator.get_output("test") == "result"
        assert orchestrator.get_output("nonexistent", "default") == "default"

    async def test_summary(self):
        """Test getting execution summary."""
        orchestrator = FSAOrchestrator()

        fsa1 = FSA(id="success", name="Success", executor=SimpleExecutor())
        fsa2 = FSA(id="fail", name="Fail", executor=FailingExecutor())

        orchestrator.add_fsa(fsa1)
        orchestrator.add_fsa(fsa2)

        await orchestrator.execute()

        summary = orchestrator.get_summary()

        assert summary["total_fsas"] == 2
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["total_duration"] > 0

    async def test_reset(self):
        """Test resetting orchestrator state."""
        orchestrator = FSAOrchestrator()

        fsa = FSA(id="test", name="Test", executor=ContextWriterExecutor("key", "value"))
        orchestrator.add_fsa(fsa)

        await orchestrator.execute()

        assert len(orchestrator.results) == 1
        assert orchestrator.context.has("key")

        orchestrator.reset()

        assert len(orchestrator.results) == 0
        assert not orchestrator.context.has("key")

    async def test_complex_workflow(self):
        """Test complex multi-level workflow."""
        orchestrator = FSAOrchestrator()

        # Level 1: Initialize
        init_fsa = FSA(
            id="init",
            name="Initialize",
            executor=ContextWriterExecutor("data", []),
        )

        # Level 2: Parallel processing
        process_fsas = []
        for i in range(3):
            fsa = FSA(
                id=f"process_{i}",
                name=f"Process {i}",
                executor=ContextWriterExecutor(f"result_{i}", i * 10),
                dependencies=["init"],
            )
            process_fsas.append(fsa)
            orchestrator.add_fsa(fsa)

        # Level 3: Aggregate
        class AggregateExecutor(FSAExecutor):
            async def execute(self, context: FSAContext) -> Any:
                total = sum(context.get(f"result_{i}", 0) for i in range(3))
                return {"total": total}

        aggregate_fsa = FSA(
            id="aggregate",
            name="Aggregate",
            executor=AggregateExecutor(),
            dependencies=[f"process_{i}" for i in range(3)],
        )

        orchestrator.add_fsa(init_fsa)
        orchestrator.add_fsa(aggregate_fsa)

        results = await orchestrator.execute()

        assert all(r.status == FSAStatus.COMPLETED for r in results.values())
        assert results["aggregate"].output == {"total": 30}

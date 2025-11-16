"""
Example implementations and usage patterns for FSA framework.

This module demonstrates how to use the FSA orchestrator for various
common workflows including data processing, agent coordination, and
code generation tasks.
"""

import asyncio
from typing import Any

from agno.fsa.orchestrator import FSA, FSAContext, FSAExecutor, FSAOrchestrator, FSAStatus
from agno.utils.log import logger


# Example 1: Simple Data Pipeline
# ================================

class LoadDataExecutor(FSAExecutor):
    """Load data from a source."""

    async def execute(self, context: FSAContext) -> Any:
        # Simulate data loading
        await asyncio.sleep(0.1)
        data = {"records": [1, 2, 3, 4, 5], "metadata": {"source": "database"}}
        context.set("raw_data", data)
        return data


class TransformDataExecutor(FSAExecutor):
    """Transform loaded data."""

    def validate(self, context: FSAContext) -> bool:
        return context.has("raw_data")

    async def execute(self, context: FSAContext) -> Any:
        raw_data = context.get("raw_data")
        # Simulate transformation
        await asyncio.sleep(0.1)
        transformed = [x * 2 for x in raw_data["records"]]
        context.set("transformed_data", transformed)
        return transformed


class SaveDataExecutor(FSAExecutor):
    """Save processed data."""

    def validate(self, context: FSAContext) -> bool:
        return context.has("transformed_data")

    async def execute(self, context: FSAContext) -> Any:
        data = context.get("transformed_data")
        # Simulate saving
        await asyncio.sleep(0.1)
        context.set("save_status", "success")
        return {"saved": len(data), "status": "success"}


async def example_data_pipeline():
    """Example: Simple data processing pipeline."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Data Processing Pipeline")
    print("=" * 60)

    # Create FSAs
    load_fsa = FSA(
        id="load",
        name="Load Data",
        executor=LoadDataExecutor(),
    )

    transform_fsa = FSA(
        id="transform",
        name="Transform Data",
        executor=TransformDataExecutor(),
        dependencies=["load"],  # Must run after load
    )

    save_fsa = FSA(
        id="save",
        name="Save Data",
        executor=SaveDataExecutor(),
        dependencies=["transform"],  # Must run after transform
    )

    # Create orchestrator
    orchestrator = FSAOrchestrator()
    orchestrator.add_fsa(load_fsa)
    orchestrator.add_fsa(transform_fsa)
    orchestrator.add_fsa(save_fsa)

    # Set progress callback
    def progress_callback(fsa_id: str, status: FSAStatus):
        print(f"  [{status.value.upper()}] {fsa_id}")

    orchestrator.set_progress_callback(progress_callback)

    # Execute
    results = await orchestrator.execute()

    # Print results
    print("\nResults:")
    for fsa_id, result in results.items():
        print(f"  {fsa_id}: {result.status.value} ({result.duration:.2f}s)")

    print(f"\nFinal data: {orchestrator.context.get('transformed_data')}")
    print(f"Summary: {orchestrator.get_summary()}")


# Example 2: Parallel Execution
# ==============================

class FetchAPIExecutor(FSAExecutor):
    """Fetch data from API."""

    def __init__(self, api_name: str):
        self.api_name = api_name

    async def execute(self, context: FSAContext) -> Any:
        # Simulate API call
        await asyncio.sleep(0.2)
        data = {self.api_name: {"status": "ok", "data": list(range(10))}}
        context.update(data)
        return data


class AggregateExecutor(FSAExecutor):
    """Aggregate data from multiple sources."""

    def __init__(self, source_keys: list):
        self.source_keys = source_keys

    def validate(self, context: FSAContext) -> bool:
        return all(context.has(key) for key in self.source_keys)

    async def execute(self, context: FSAContext) -> Any:
        # Simulate aggregation
        await asyncio.sleep(0.1)
        total = sum(
            len(context.get(key, {}).get("data", []))
            for key in self.source_keys
        )
        result = {"total_records": total, "sources": len(self.source_keys)}
        context.set("aggregated", result)
        return result


async def example_parallel_execution():
    """Example: Parallel API fetching with aggregation."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Parallel Execution")
    print("=" * 60)

    orchestrator = FSAOrchestrator()

    # Create parallel fetch FSAs (no dependencies = run in parallel)
    api_names = ["users", "products", "orders"]
    for api_name in api_names:
        fsa = FSA(
            id=f"fetch_{api_name}",
            name=f"Fetch {api_name.title()}",
            executor=FetchAPIExecutor(api_name),
        )
        orchestrator.add_fsa(fsa)

    # Create aggregation FSA (depends on all fetches)
    aggregate_fsa = FSA(
        id="aggregate",
        name="Aggregate Data",
        executor=AggregateExecutor(api_names),
        dependencies=[f"fetch_{name}" for name in api_names],
    )
    orchestrator.add_fsa(aggregate_fsa)

    # Execute
    start_time = asyncio.get_event_loop().time()
    results = await orchestrator.execute()
    duration = asyncio.get_event_loop().time() - start_time

    # Print results
    print(f"\nTotal execution time: {duration:.2f}s")
    print(f"(Parallel execution saved ~{0.6 - duration:.2f}s vs sequential)")
    print(f"\nAggregated result: {orchestrator.context.get('aggregated')}")


# Example 3: Error Handling and Retries
# ======================================

class UnreliableExecutor(FSAExecutor):
    """Executor that fails randomly then succeeds."""

    def __init__(self):
        self.attempts = 0

    async def execute(self, context: FSAContext) -> Any:
        self.attempts += 1
        if self.attempts < 3:
            raise Exception(f"Simulated failure (attempt {self.attempts})")
        return {"success": True, "attempts": self.attempts}


async def example_error_handling():
    """Example: Error handling with retries."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Error Handling and Retries")
    print("=" * 60)

    fsa = FSA(
        id="unreliable_task",
        name="Unreliable Task",
        executor=UnreliableExecutor(),
        max_retries=3,
        retry_delay=0.1,
    )

    orchestrator = FSAOrchestrator()
    orchestrator.add_fsa(fsa)

    results = await orchestrator.execute()

    result = results["unreliable_task"]
    print(f"\nStatus: {result.status.value}")
    print(f"Output: {result.output}")
    print(f"Duration: {result.duration:.2f}s")


# Example 4: Conditional Execution
# =================================

class CheckConditionExecutor(FSAExecutor):
    """Set a condition flag."""

    async def execute(self, context: FSAContext) -> Any:
        context.set("should_process", True)
        return {"condition_set": True}


class ConditionalExecutor(FSAExecutor):
    """Execute only if condition is met."""

    async def execute(self, context: FSAContext) -> Any:
        return {"processed": True}


async def example_conditional_execution():
    """Example: Conditional FSA execution."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Conditional Execution")
    print("=" * 60)

    orchestrator = FSAOrchestrator()

    check_fsa = FSA(
        id="check",
        name="Check Condition",
        executor=CheckConditionExecutor(),
    )

    conditional_fsa = FSA(
        id="conditional",
        name="Conditional Task",
        executor=ConditionalExecutor(),
        dependencies=["check"],
        condition=lambda ctx: ctx.get("should_process", False),
    )

    skip_fsa = FSA(
        id="skip",
        name="Skip Task",
        executor=ConditionalExecutor(),
        dependencies=["check"],
        condition=lambda ctx: ctx.get("should_skip", False),  # Will be skipped
    )

    orchestrator.add_fsa(check_fsa)
    orchestrator.add_fsa(conditional_fsa)
    orchestrator.add_fsa(skip_fsa)

    results = await orchestrator.execute()

    print("\nResults:")
    for fsa_id, result in results.items():
        print(f"  {fsa_id}: {result.status.value}")


# Example 5: Agent Coordination
# ==============================

class AgentTaskExecutor(FSAExecutor):
    """Simulate an agent executing a task."""

    def __init__(self, agent_name: str, task: str):
        self.agent_name = agent_name
        self.task = task

    async def execute(self, context: FSAContext) -> Any:
        # Simulate agent work
        await asyncio.sleep(0.15)
        result = {
            "agent": self.agent_name,
            "task": self.task,
            "status": "completed",
        }
        context.set(f"{self.agent_name}_result", result)
        return result


async def example_agent_coordination():
    """Example: Coordinating multiple agents."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Agent Coordination")
    print("=" * 60)

    orchestrator = FSAOrchestrator()

    # Research agent
    research_fsa = FSA(
        id="research",
        name="Research Agent",
        executor=AgentTaskExecutor("research_agent", "gather information"),
        priority=10,  # High priority
    )

    # Analysis agents (parallel, after research)
    sentiment_fsa = FSA(
        id="sentiment",
        name="Sentiment Analysis Agent",
        executor=AgentTaskExecutor("sentiment_agent", "analyze sentiment"),
        dependencies=["research"],
    )

    summary_fsa = FSA(
        id="summary",
        name="Summary Agent",
        executor=AgentTaskExecutor("summary_agent", "create summary"),
        dependencies=["research"],
    )

    # Report agent (after all analysis)
    report_fsa = FSA(
        id="report",
        name="Report Generation Agent",
        executor=AgentTaskExecutor("report_agent", "generate report"),
        dependencies=["sentiment", "summary"],
    )

    orchestrator.add_fsa(research_fsa)
    orchestrator.add_fsa(sentiment_fsa)
    orchestrator.add_fsa(summary_fsa)
    orchestrator.add_fsa(report_fsa)

    results = await orchestrator.execute()

    print("\nAgent Results:")
    for fsa_id, result in results.items():
        print(f"  {fsa_id}: {result.status.value} ({result.duration:.2f}s)")

    print(f"\nTotal duration: {sum(r.duration for r in results.values()):.2f}s")
    print(f"Summary: {orchestrator.get_summary()}")


# Main runner
# ===========

async def run_all_examples():
    """Run all examples."""
    await example_data_pipeline()
    await example_parallel_execution()
    await example_error_handling()
    await example_conditional_execution()
    await example_agent_coordination()


if __name__ == "__main__":
    asyncio.run(run_all_examples())

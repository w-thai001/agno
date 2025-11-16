"""🎭 Meta-FSA Orchestrator Example

This example demonstrates using the Meta-FSA Orchestrator to coordinate multiple FSAs
working together on a complex workflow.

Run `pip install agno openai` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.fsa.meta_orchestrator import MetaFSAOrchestrator
from agno.fsa.task_deconstructor import MLATaskDeconstructor
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.code_optimizer import RSICodeOptimizer
from agno.fsa.quality_validator import CodeQualityValidator


def main():
    """Demonstrate Meta-FSA Orchestrator"""

    # Create a coding agent
    agent = Agent(
        name="DevelopmentAgent",
        model=OpenAIChat(id="gpt-4o"),
        description="Full-stack software engineer",
        markdown=True
    )

    # Create FSAs
    task_deconstructor = MLATaskDeconstructor(
        name="TaskAnalyzer",
        analysis_agent=agent
    )

    code_builder = MultiStepCodeBuilder(
        name="CodeBuilder",
        code_agent=agent,
        programming_language="python"
    )

    optimizer = RSICodeOptimizer(
        name="Optimizer",
        optimization_agent=agent
    )

    validator = CodeQualityValidator(
        name="QualityValidator",
        validation_agent=agent,
        min_overall_score=70.0
    )

    # Create Meta-FSA Orchestrator
    orchestrator = MetaFSAOrchestrator(
        name="DevelopmentOrchestrator",
        allow_partial_success=True,
        parallel_execution=True,
        max_parallel_fsas=3,
        debug_mode=True
    )

    # Register FSAs with dependencies
    task_id = orchestrator.register_fsa(task_deconstructor)
    builder_id = orchestrator.register_fsa(code_builder, depends_on=[task_id])
    optimizer_id = orchestrator.register_fsa(optimizer, depends_on=[builder_id])
    validator_id = orchestrator.register_fsa(validator, depends_on=[optimizer_id])

    print("\n" + "=" * 60)
    print("META-FSA ORCHESTRATOR - COORDINATED DEVELOPMENT WORKFLOW")
    print("=" * 60)

    # Run orchestrated workflow
    result = orchestrator.run({
        "task": "Build a REST API for a todo application with CRUD operations",
        "language": "python",
        "framework": "FastAPI"
    })

    print(f"\nOrchestration Success: {result.success}")
    print(f"Total Execution Time: {result.total_execution_time:.2f}s")
    print(f"FSAs Executed: {len(result.fsa_results)}")

    if result.execution_plan:
        print(f"\n📋 EXECUTION PLAN:")
        print(f"   Stages: {len(result.execution_plan.execution_order)}")
        for i, stage in enumerate(result.execution_plan.execution_order, 1):
            print(f"   Stage {i}: {len(stage)} FSA(s) in parallel")

    print(f"\n✅ SUCCESSFUL FSAs: {len(result.successful_fsas)}")
    for fsa_id in result.successful_fsas:
        fsa_name = orchestrator.fsas[fsa_id].name
        fsa_result = result.fsa_results[fsa_id]
        print(f"   ✓ {fsa_name}: {fsa_result.final_state}")

    if result.failed_fsas:
        print(f"\n❌ FAILED FSAs: {len(result.failed_fsas)}")
        for fsa_id in result.failed_fsas:
            fsa_name = orchestrator.fsas[fsa_id].name
            print(f"   ✗ {fsa_name}")

    print("\n📊 FSA RESULTS SUMMARY:")
    for fsa_id, fsa_result in result.fsa_results.items():
        fsa_name = orchestrator.fsas[fsa_id].name
        print(f"\n   {fsa_name}:")
        print(f"      Final State: {fsa_result.final_state}")
        print(f"      Execution Time: {fsa_result.execution_time:.2f}s")
        print(f"      State Transitions: {len(fsa_result.state_history)}")

    print("\n" + orchestrator.get_execution_summary())


if __name__ == "__main__":
    main()

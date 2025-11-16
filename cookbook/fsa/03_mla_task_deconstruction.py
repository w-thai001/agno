"""📊 MLA Task Deconstruction Example

This example demonstrates using Maximum Leverage Analysis (MLA) to deconstruct
complex tasks into prioritized subtasks based on impact and effort.

Run `pip install agno openai` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.fsa.task_deconstructor import MLATaskDeconstructor


def main():
    """Demonstrate MLA Task Deconstruction"""

    # Create an agent for task analysis
    analysis_agent = Agent(
        name="TaskAnalyzer",
        model=OpenAIChat(id="gpt-4o"),
        description="Expert at breaking down complex tasks using MLA principles",
        markdown=True
    )

    # Create MLA deconstructor
    deconstructor = MLATaskDeconstructor(
        name="ProjectDeconstructor",
        analysis_agent=analysis_agent,
        leverage_threshold=2.0,  # Minimum leverage score (impact/effort)
        debug_mode=True
    )

    # Deconstruct a complex task
    result = deconstructor.run({
        "task": "Build a complete e-commerce platform with user authentication, product catalog, shopping cart, payment integration, and admin dashboard"
    })

    print("\n" + "=" * 60)
    print("MLA TASK DECONSTRUCTION RESULTS")
    print("=" * 60)

    print(f"\nOriginal Task: {result.original_task}")
    print(f"Complexity: {result.analysis.complexity}")
    print(f"Total Estimated Effort: {result.total_estimated_effort} hours")
    print(f"Expected Impact: {result.expected_impact}/10")
    print(f"Overall Leverage: {result.overall_leverage:.2f}")

    print("\n🎯 HIGH LEVERAGE ACTIONS (Focus on these first):")
    for i, action in enumerate(result.high_leverage_actions, 1):
        print(f"  {i}. {action}")

    print("\n⚠️  LOW LEVERAGE ACTIONS (Defer or eliminate):")
    for i, action in enumerate(result.low_leverage_actions, 1):
        print(f"  {i}. {action}")

    print("\n♻️  REUSABLE COMPONENTS:")
    for i, component in enumerate(result.reusable_components, 1):
        print(f"  {i}. {component}")

    print("\n📋 SUBTASKS BREAKDOWN:")
    for subtask in result.subtasks[:5]:  # Show first 5
        print(f"\n  [{subtask.category.upper()}] {subtask.description}")
        print(f"     Impact: {subtask.leverage_score.impact}/10")
        print(f"     Effort: {subtask.leverage_score.effort}/10")
        print(f"     Leverage: {subtask.leverage_score.leverage:.2f}")
        print(f"     Duration: {subtask.estimated_duration} hours")

    print("\n" + deconstructor.get_leverage_report())


if __name__ == "__main__":
    main()

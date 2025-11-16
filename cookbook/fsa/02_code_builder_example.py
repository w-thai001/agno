"""🏗️ Multi-Step Code Builder Example

This example demonstrates using the Multi-Step Code Builder FSA to generate code
through structured phases: requirements → design → implementation → testing → documentation.

Run `pip install agno openai` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.fsa.code_builder import MultiStepCodeBuilder


def main():
    """Demonstrate Multi-Step Code Builder"""

    # Create an agent for code generation
    coding_agent = Agent(
        name="CodingAgent",
        model=OpenAIChat(id="gpt-4o"),
        description="Expert software engineer",
        markdown=True
    )

    # Create code builder FSA
    builder = MultiStepCodeBuilder(
        name="UserAuthBuilder",
        code_agent=coding_agent,
        programming_language="python",
        framework="FastAPI",
        include_tests=True,
        include_documentation=True,
        debug_mode=True
    )

    # Build a feature
    result = builder.run({
        "task": "Create a user authentication system with JWT tokens",
        "language": "python",
        "framework": "FastAPI"
    })

    print("\n" + "=" * 60)
    print("CODE BUILDER RESULTS")
    print("=" * 60)
    print(f"\nSuccess: {result.success}")
    print(f"Artifacts generated: {len(result.artifacts)}")

    for artifact in result.artifacts:
        print(f"\n📄 {artifact.name}")
        print(f"   Language: {artifact.language}")
        print(f"   Description: {artifact.description}")

    if result.requirements:
        print(f"\n✅ Requirements: {len(result.requirements.functional_requirements)} functional")

    if result.design:
        print(f"\n🏗️  Design: {len(result.design.components)} components")

    print(f"\n📊 Test Results: {result.test_results}")

    print("\n" + builder.get_build_summary())


if __name__ == "__main__":
    main()

"""🤖 Basic FSA Usage

This example demonstrates basic FSA (Finite State Automaton) usage with the Agno framework.
FSAs provide structured state management for agentic systems.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.base import FSA, FSAState, FSATransition


def main():
    """Demonstrate basic FSA usage"""

    # Create a simple FSA
    fsa = FSA(
        name="BasicExample",
        initial_state=FSAState.INITIAL,
        debug_mode=True
    )

    # Add transitions
    fsa.add_transition(
        FSAState.INITIAL,
        FSAState.RUNNING,
        action=lambda ctx: {**ctx, "started": True},
        description="Start execution"
    )

    fsa.add_transition(
        FSAState.RUNNING,
        FSAState.SUCCESS,
        condition=lambda ctx: ctx.get("started", False),
        description="Complete successfully"
    )

    # Run the FSA
    result = fsa.run(initial_context={"input": "test"})

    print(f"FSA completed in state: {result.final_state}")
    print(f"Success: {result.success}")
    print(f"State history: {result.state_history}")
    print(f"Execution time: {result.execution_time:.3f}s")


if __name__ == "__main__":
    main()

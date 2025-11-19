"""
Simple FSA Workflow Example

A minimal example showing the core FSA workflow engine functionality.
"""

from agno.workflow.fsa import (
    FSAEngine,
    State,
    StateType,
    Transition,
    TransitionCondition,
    StateContext,
)


def main():
    """Run a simple 3-state workflow"""

    # Define state actions
    def start_action(ctx: StateContext):
        print("Starting workflow...")
        ctx.data["count"] = 0
        return True

    def process_action(ctx: StateContext):
        print("Processing data...")
        ctx.data["count"] += 10
        return ctx.data["count"]

    def end_action(ctx: StateContext):
        print(f"Workflow complete! Final count: {ctx.data['count']}")
        return ctx.data

    # Create states
    states = {
        "start": State(
            name="start",
            state_type=StateType.START,
            action=start_action,
        ),
        "process": State(
            name="process",
            state_type=StateType.INTERMEDIATE,
            action=process_action,
        ),
        "end": State(
            name="end",
            state_type=StateType.END,
            action=end_action,
        ),
    }

    # Create transitions
    transitions = [
        Transition("start", "process", TransitionCondition.SUCCESS),
        Transition("process", "end", TransitionCondition.SUCCESS),
    ]

    # Create and run engine
    engine = FSAEngine(
        states=states,
        transitions=transitions,
        initial_state="start",
    )

    # Execute workflow
    context = engine.run()

    # Print results
    print("\nExecution Results:")
    print(f"- States visited: {' -> '.join(context.history)}")
    print(f"- Total transitions: {context.metadata['execution']['total_transitions']}")
    print(f"- Duration: {context.metadata['execution']['duration_ms']:.2f}ms")


if __name__ == "__main__":
    main()

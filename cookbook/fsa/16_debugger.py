"""🐛 FSA Debugger Example

This example demonstrates interactive debugging of FSA execution with breakpoints,
step-through, variable inspection, and execution history.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.debugger import FSADebugger, DebugCommand, BreakpointType
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.task_deconstructor import MLATaskDeconstructor


def main():
    """Demonstrate FSA Debugger"""

    print("\n" + "=" * 70)
    print("FSA DEBUGGER - INTERACTIVE DEVELOPMENT TOOL")
    print("=" * 70)

    # =========================================================================
    # Example 1: Basic Debugging with Breakpoints
    # =========================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: BASIC DEBUGGING WITH BREAKPOINTS")
    print("─" * 70)

    # Create FSA to debug
    code_builder = MultiStepCodeBuilder(
        name="CodeBuilder",
        programming_language="python",
        max_iterations=3
    )

    # Create debugger
    debugger = FSADebugger(name="Debugger", debug_mode=True)

    print("\n🔧 Creating debugger and attaching to FSA...")

    # Attach to FSA
    debugger.attach(code_builder)

    print(f"✓ Debugger attached to: {code_builder.name}")

    # Set breakpoints
    print("\n🔴 Setting breakpoints:")

    bp1 = debugger.set_breakpoint("analyzing_requirements", breakpoint_type="state")
    print(f"   1. State breakpoint at 'analyzing_requirements' (ID: {bp1})")

    bp2 = debugger.set_breakpoint("implementing", breakpoint_type="state")
    print(f"   2. State breakpoint at 'implementing' (ID: {bp2})")

    bp3 = debugger.set_breakpoint(
        "testing",
        breakpoint_type="state",
        condition="len(ctx.get('code', '')) > 100"
    )
    print(f"   3. Conditional breakpoint at 'testing' (ID: {bp3})")
    print(f"      Condition: Code length > 100 chars")

    # Watch variables
    print("\n👀 Setting watches:")

    debugger.watch_variable("task")
    debugger.watch_variable("code")
    debugger.watch_variable("current_iteration")

    print("   - Watching: task, code, current_iteration")

    # =========================================================================
    # Example 2: Step-Through Execution
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: STEP-THROUGH EXECUTION")
    print("=" * 70)

    print("\n▶️  Starting step-through debugging...")
    print("    (Simulating user stepping through execution)")

    # Simulate stepping
    steps = []

    for i in range(5):
        print(f"\n  Step {i + 1}:")

        # Execute one step
        result = debugger.run({"command": DebugCommand.STEP})

        # Get current frame
        frame = debugger.get_current_frame()

        if frame:
            print(f"    State: {frame.state}")
            print(f"    Timestamp: {frame.timestamp}")
            print(f"    Transition count: {frame.transition_count}")

            # Show watched variables
            watches = debugger.get_watches()
            if watches:
                print(f"    Watches:")
                for watch in watches:
                    if watch.variable_name in frame.context:
                        value = frame.context[watch.variable_name]
                        # Truncate long values
                        value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        print(f"      {watch.variable_name} = {value_str}")
                        if watch.change_count > 0:
                            print(f"        (changed {watch.change_count} times)")

        # Check if hit breakpoint
        breakpoints = debugger.get_breakpoints()
        for bp in breakpoints:
            if bp.hit_count > 0:
                print(f"    ⚠️  Breakpoint hit: {bp.location} (hit {bp.hit_count} times)")

        # Check if reached final state
        if code_builder.current_state in code_builder.final_states:
            print(f"\n  ✅ Reached final state: {code_builder.current_state}")
            break

    # =========================================================================
    # Example 3: Inspection and Backtrace
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: STATE INSPECTION & BACKTRACE")
    print("=" * 70)

    # Inspect current state
    print("\n🔍 Inspecting current state:")

    inspect_result = debugger.run({"command": DebugCommand.INSPECT})
    inspection = inspect_result.context.get("inspection", {})

    if inspection:
        print(f"\n  Current State: {inspection.get('current_state')}")
        print(f"  Transitions Executed: {inspection.get('transitions_executed')}")

        print(f"\n  State History:")
        history = inspection.get('state_history', [])
        for i, state in enumerate(history[-5:], 1):  # Last 5 states
            print(f"    {i}. {state}")

        print(f"\n  Context Variables:")
        context = inspection.get('context', {})
        for key, value in list(context.items())[:5]:  # First 5 variables
            value_str = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
            print(f"    {key}: {value_str}")

    # Get backtrace
    print("\n📜 Execution Backtrace:")

    backtrace = debugger.get_backtrace()
    print(f"\n  Total Frames: {len(backtrace)}")
    print(f"\n  Recent Frames:")

    for i, frame in enumerate(backtrace[-5:], 1):  # Last 5 frames
        print(f"    {i}. State: {frame.state}")
        print(f"       Time: {frame.timestamp}")
        print(f"       Transitions: {frame.transition_count}")

    # =========================================================================
    # Example 4: Breakpoint Management
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: BREAKPOINT MANAGEMENT")
    print("=" * 70)

    print("\n🔴 Current Breakpoints:")

    breakpoints = debugger.get_breakpoints()
    for i, bp in enumerate(breakpoints, 1):
        status = "✓ Enabled" if bp.enabled else "✗ Disabled"
        condition_str = f" [Condition: {bp.condition}]" if bp.condition else ""
        print(f"  {i}. {bp.breakpoint_id}: {bp.type.value} at '{bp.location}'")
        print(f"     {status} | Hit count: {bp.hit_count}{condition_str}")

    # Disable a breakpoint
    if breakpoints:
        bp_to_disable = breakpoints[0].breakpoint_id
        debugger.disable_breakpoint(bp_to_disable)
        print(f"\n  ⏸️  Disabled breakpoint: {bp_to_disable}")

    # Enable it back
        debugger.enable_breakpoint(bp_to_disable)
        print(f"  ▶️  Re-enabled breakpoint: {bp_to_disable}")

    # Remove a breakpoint
    if len(breakpoints) > 1:
        bp_to_remove = breakpoints[-1].breakpoint_id
        debugger.remove_breakpoint(bp_to_remove)
        print(f"  🗑️  Removed breakpoint: {bp_to_remove}")

    # =========================================================================
    # Example 5: Variable Watches
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 5: VARIABLE WATCHES")
    print("=" * 70)

    print("\n👀 Watched Variables:")

    watches = debugger.get_watches()
    for i, watch in enumerate(watches, 1):
        value_str = str(watch.last_value)[:50] + "..." if watch.last_value and len(str(watch.last_value)) > 50 else str(watch.last_value)
        print(f"  {i}. {watch.variable_name}")
        print(f"     Last value: {value_str}")
        print(f"     Changes: {watch.change_count}")

    # Add callback for variable changes
    print("\n🔔 Setting up change notifications:")

    def on_variable_change(var_name, old_value, new_value):
        print(f"  📢 Variable '{var_name}' changed!")
        print(f"     Old: {old_value}")
        print(f"     New: {new_value}")

    debugger.on_variable_changed = on_variable_change
    print("  ✓ Change callback registered")

    # =========================================================================
    # Example 6: Debug Session Info
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 6: DEBUG SESSION INFORMATION")
    print("=" * 70)

    session = debugger.get_debug_session()

    print(f"\n📊 Debug Session:")
    print(f"  Session ID: {session.session_id}")
    print(f"  FSA Name: {session.fsa_name}")
    print(f"  Start Time: {session.start_time}")
    print(f"  Breakpoints: {len(session.breakpoints)}")
    print(f"  Watches: {len(session.watches)}")
    print(f"  Execution History: {len(session.execution_history)} frames")
    print(f"  Current Frame: {session.current_frame_index}")

    # =========================================================================
    # Example 7: Debugging Complex FSA
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 7: DEBUGGING COMPLEX FSA")
    print("=" * 70)

    print("\n🔧 Creating complex FSA (Task Deconstructor)...")

    task_deconstructor = MLATaskDeconstructor(
        name="TaskAnalyzer",
        min_impact_threshold=3.0,
        max_subtasks=5
    )

    # Create new debugger for this FSA
    debugger2 = FSADebugger(name="Debugger2", debug_mode=True)
    debugger2.attach(task_deconstructor)

    print(f"✓ Debugger attached to: {task_deconstructor.name}")

    # Set strategic breakpoints
    print("\n🔴 Setting strategic breakpoints:")

    bp_analyze = debugger2.set_breakpoint("analyzing", breakpoint_type="state")
    bp_decompose = debugger2.set_breakpoint("decomposing", breakpoint_type="state")
    bp_prioritize = debugger2.set_breakpoint("prioritizing", breakpoint_type="state")

    print(f"   - Analysis phase: {bp_analyze}")
    print(f"   - Decomposition phase: {bp_decompose}")
    print(f"   - Prioritization phase: {bp_prioritize}")

    # Watch key variables
    debugger2.watch_variable("task")
    debugger2.watch_variable("subtasks")
    debugger2.watch_variable("leverage_scores")

    print("\n👀 Watching: task, subtasks, leverage_scores")

    # Execute with continue (run until breakpoint)
    print("\n▶️  Running with continue command...")
    print("    (Will pause at first breakpoint)")

    continue_result = debugger2.run({"command": DebugCommand.CONTINUE})

    if debugger2.paused:
        current_frame = debugger2.get_current_frame()
        if current_frame:
            print(f"\n⏸️  Paused at state: {current_frame.state}")

    # =========================================================================
    # Best Practices
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("DEBUGGING BEST PRACTICES")
    print("=" * 70)

    practices = [
        "1. Set breakpoints at critical state transitions",
        "2. Use conditional breakpoints for specific scenarios",
        "3. Watch variables that change frequently or unexpectedly",
        "4. Review execution history to understand state flow",
        "5. Use step-through for detailed analysis",
        "6. Use continue for quick iteration between breakpoints",
        "7. Inspect context variables to verify assumptions",
        "8. Enable debug mode for detailed logging",
        "9. Remove or disable unused breakpoints",
        "10. Save debug sessions for later analysis"
    ]

    for practice in practices:
        print(f"   {practice}")

    # =========================================================================
    # Common Debug Commands
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("COMMON DEBUG COMMANDS")
    print("=" * 70)

    commands = {
        "step (s)": "Execute one transition",
        "step_over": "Execute until next state",
        "continue (c)": "Run until breakpoint or completion",
        "break <state>": "Set breakpoint at state",
        "watch <var>": "Watch variable for changes",
        "inspect (i)": "Inspect current state and context",
        "backtrace (bt)": "Show execution history",
        "quit (q)": "Stop debugging"
    }

    for cmd, desc in commands.items():
        print(f"   {cmd:20} - {desc}")

    print("\n" + "=" * 70)
    print("✅ FSA Debugger demonstration complete!")
    print("=" * 70)

    print("\n💡 Tip: Use interactive mode with debugger.debug_run(interactive=True)")
    print("    for a full interactive debugging console!")


if __name__ == "__main__":
    main()

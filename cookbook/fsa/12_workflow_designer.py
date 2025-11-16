"""🎨 FSA Workflow Designer Example

This example demonstrates visual FSA creation without writing code.

Run `pip install agno pyyaml` to install dependencies.
"""

from agno.fsa.workflow_designer import (
    FSAWorkflowDesigner,
    FSADesign,
    StateDefinition,
    TransitionDefinition
)


def main():
    """Demonstrate FSA Workflow Designer"""

    print("\n" + "=" * 60)
    print("FSA WORKFLOW DESIGNER")
    print("=" * 60)

    # Create designer
    designer = FSAWorkflowDesigner(name="Designer", debug_mode=True)

    # Example 1: Create FSA from template
    print("\n--- Example 1: Using Templates ---")
    print("\nAvailable templates:", list(designer.templates.keys()))

    result1 = designer.run({"template": "simple_sequential", "export_format": "python"})
    print("\n✅ Generated code from template:")
    print(result1.context.get("exported_code", "")[:500] + "...")

    # Example 2: Create custom design
    print("\n\n--- Example 2: Custom Design ---")

    custom_design = FSADesign(
        name="UserOnboarding",
        description="User onboarding workflow",
        states=[
            StateDefinition(
                name="initial",
                is_initial=True,
                description="User starts onboarding"
            ),
            StateDefinition(
                name="collect_info",
                description="Collect user information"
            ),
            StateDefinition(
                name="verify_email",
                description="Verify email address"
            ),
            StateDefinition(
                name="setup_profile",
                description="Setup user profile"
            ),
            StateDefinition(
                name="completed",
                is_final=True,
                description="Onboarding complete"
            ),
            StateDefinition(
                name="failed",
                is_final=True,
                description="Onboarding failed"
            )
        ],
        transitions=[
            TransitionDefinition(
                from_state="initial",
                to_state="collect_info",
                description="Start onboarding"
            ),
            TransitionDefinition(
                from_state="collect_info",
                to_state="verify_email",
                condition_code='lambda ctx: ctx.get("info_collected", False)',
                description="Info collected"
            ),
            TransitionDefinition(
                from_state="verify_email",
                to_state="setup_profile",
                condition_code='lambda ctx: ctx.get("email_verified", False)',
                description="Email verified"
            ),
            TransitionDefinition(
                from_state="verify_email",
                to_state="failed",
                condition_code='lambda ctx: not ctx.get("email_verified", False)',
                description="Email verification failed"
            ),
            TransitionDefinition(
                from_state="setup_profile",
                to_state="completed",
                description="Profile setup complete"
            )
        ]
    )

    # Generate code
    designer.reset()
    result2 = designer.run({"design": custom_design, "export_format": "python"})

    print("\n✅ Generated UserOnboarding FSA:")
    print("\n" + result2.context.get("exported_code", ""))

    # Example 3: Export to different formats
    print("\n\n--- Example 3: Export to JSON ---")
    designer.reset()
    designer.current_design = custom_design
    result3 = designer.run({"design": custom_design, "export_format": "json"})

    print("\n✅ Design as JSON:")
    print(result3.context.get("exported_code", "")[:300] + "...")

    # Example 4: State diagram
    print("\n\n--- Example 4: State Diagram (Mermaid) ---")
    designer.current_design = custom_design
    diagram = designer.get_state_diagram_mermaid()

    print("\n✅ Mermaid State Diagram:")
    print(diagram)

    # Example 5: Save and load
    print("\n\n--- Example 5: Save and Load Design ---")

    # Save design
    designer.current_design = custom_design
    design_file = "/tmp/user_onboarding_design.json"
    designer.save_design(design_file, format="json")
    print(f"\n✅ Saved design to: {design_file}")

    # Load design
    loaded_design = designer.load_design_from_file(design_file)
    print(f"✅ Loaded design: {loaded_design.name}")
    print(f"   States: {len(loaded_design.states)}")
    print(f"   Transitions: {len(loaded_design.transitions)}")

    # Example 6: Export to Python file
    print("\n\n--- Example 6: Export to Python File ---")
    python_file = "/tmp/user_onboarding_fsa.py"
    designer.current_design = custom_design
    designer.export_to_python(python_file)
    print(f"\n✅ Exported to Python file: {python_file}")

    # Show summary
    print("\n" + "=" * 60)
    print("DESIGN SUMMARY")
    print("=" * 60)
    print(f"\nName: {custom_design.name}")
    print(f"Description: {custom_design.description}")
    print(f"States: {len(custom_design.states)}")
    print(f"Transitions: {len(custom_design.transitions)}")

    print("\n📊 States:")
    for state in custom_design.states:
        flags = []
        if state.is_initial:
            flags.append("INITIAL")
        if state.is_final:
            flags.append("FINAL")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"   - {state.name}{flag_str}: {state.description}")

    print("\n🔀 Transitions:")
    for trans in custom_design.transitions:
        print(f"   {trans.from_state} → {trans.to_state}")
        if trans.description:
            print(f"      ({trans.description})")


if __name__ == "__main__":
    main()

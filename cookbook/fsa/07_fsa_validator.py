"""🔍 FSA Validator Example

This example demonstrates using the FSA Validator to validate FSA definitions
for correctness, completeness, and best practices.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.base import FSA, FSAState
from agno.fsa.fsa_validator import FSAValidator
from agno.fsa.code_builder import MultiStepCodeBuilder


def create_good_fsa():
    """Create a well-formed FSA"""
    fsa = FSA(name="GoodFSA", initial_state=FSAState.INITIAL)

    fsa.add_transition(
        FSAState.INITIAL,
        FSAState.RUNNING,
        action=lambda ctx: {**ctx, "started": True}
    )

    fsa.add_transition(
        FSAState.RUNNING,
        FSAState.SUCCESS,
        condition=lambda ctx: ctx.get("started", False)
    )

    return fsa


def create_problematic_fsa():
    """Create an FSA with issues"""
    from enum import Enum

    class ProblematicState(str, Enum):
        INITIAL = "initial"
        STATE_A = "state_a"
        STATE_B = "state_b"
        UNREACHABLE = "unreachable"
        DEADLOCK = "deadlock"
        SUCCESS = "success"

    fsa = FSA(name="ProblematicFSA", initial_state=ProblematicState.INITIAL)

    # Add some transitions
    fsa.add_transition(ProblematicState.INITIAL, ProblematicState.STATE_A)
    fsa.add_transition(ProblematicState.STATE_A, ProblematicState.STATE_B)

    # UNREACHABLE state has no incoming transitions
    # DEADLOCK state has no outgoing transitions
    fsa.add_transition(ProblematicState.INITIAL, ProblematicState.DEADLOCK)

    fsa.final_states = {ProblematicState.SUCCESS}

    return fsa


def main():
    """Demonstrate FSA Validator"""

    print("\n" + "=" * 60)
    print("FSA VALIDATOR EXAMPLES")
    print("=" * 60)

    # Example 1: Validate a good FSA
    print("\n--- Example 1: Validating a Well-Formed FSA ---")
    good_fsa = create_good_fsa()
    validator = FSAValidator(name="Validator1", debug_mode=True)

    result = validator.run({"fsa": good_fsa})

    print(f"\nValidation Result: {'✅ VALID' if result.valid else '❌ INVALID'}")
    print(f"Critical Issues: {result.critical_issues}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    print(f"Info: {result.info}")

    print("\n📊 FSA Metrics:")
    print(f"   States: {result.metrics.total_states}")
    print(f"   Transitions: {result.metrics.total_transitions}")
    print(f"   Reachable States: {result.metrics.reachable_states}")
    print(f"   Max Depth: {result.metrics.max_depth}")
    print(f"   Complexity: {result.metrics.complexity_score}/100")

    if result.passed_checks:
        print("\n✅ Passed Checks:")
        for check in result.passed_checks:
            print(f"   - {check}")

    # Example 2: Validate a problematic FSA
    print("\n\n--- Example 2: Validating a Problematic FSA ---")
    bad_fsa = create_problematic_fsa()
    validator2 = FSAValidator(name="Validator2")

    result2 = validator2.run({"fsa": bad_fsa})

    print(f"\nValidation Result: {'✅ VALID' if result2.valid else '❌ INVALID'}")
    print(f"Critical Issues: {result2.critical_issues}")
    print(f"Errors: {result2.errors}")
    print(f"Warnings: {result2.warnings}")

    if result2.issues:
        print("\n🐛 Issues Found:")
        for i, issue in enumerate(result2.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "error": "🟠",
                "warning": "🟡",
                "info": "🔵"
            }
            icon = severity_icon.get(issue.severity.value, "⚪")
            print(f"\n   {i}. {icon} [{issue.severity.value.upper()}] {issue.category.value}")
            print(f"      {issue.description}")
            if issue.state:
                print(f"      State: {issue.state}")
            print(f"      💡 {issue.recommendation}")

    if result2.recommendations:
        print("\n💡 Recommendations:")
        for rec in result2.recommendations:
            print(f"   - {rec}")

    # Example 3: Validate a complex FSA (Code Builder)
    print("\n\n--- Example 3: Validating Complex FSA (Code Builder) ---")
    code_builder = MultiStepCodeBuilder(name="CodeBuilder")
    validator3 = FSAValidator(name="Validator3")

    result3 = validator3.run({"fsa": code_builder})

    print(f"\nValidation Result: {'✅ VALID' if result3.valid else '❌ INVALID'}")
    print(f"\n📊 Complexity Analysis:")
    print(f"   States: {result3.metrics.total_states}")
    print(f"   Transitions: {result3.metrics.total_transitions}")
    print(f"   Max Depth: {result3.metrics.max_depth}")
    print(f"   Avg Branching Factor: {result3.metrics.average_branching_factor:.2f}")
    print(f"   Has Cycles: {'Yes' if result3.metrics.has_cycles else 'No'}")

    print("\n" + validator3.get_validation_report())


if __name__ == "__main__":
    main()

"""Example: Generating FSAs using FSAGeneratorFSA

This example demonstrates how to use the FSA Generator to create
custom FSA implementations from specifications.
"""

from pathlib import Path
from agno.fsa import FSAGeneratorFSA, FSASpecification
from agno.utils.log import logger

# Configure logging
logger.setLevel("INFO")


def example_basic_fsa_generation():
    """Generate a basic FSA."""
    print("\n" + "=" * 60)
    print("Example 1: Basic FSA Generation")
    print("=" * 60)

    # Create FSA specification
    spec = FSASpecification(
        name="DataProcessorFSA",
        purpose="FSA for processing data through multiple stages",
        states={"initial", "loading", "processing", "validating", "completed", "error"},
        stateful=True,
        cascade_aware=False,
        custom_transitions=[
            {"from_state": "initial", "to_state": "loading"},
            {"from_state": "loading", "to_state": "processing"},
            {"from_state": "processing", "to_state": "validating"},
            {"from_state": "validating", "to_state": "completed"},
            {"from_state": "loading", "to_state": "error"},
            {"from_state": "processing", "to_state": "error"},
            {"from_state": "validating", "to_state": "error"},
        ]
    )

    # Create generator
    generator = FSAGeneratorFSA(
        output_dir=Path("/tmp/fsa_examples/generated"),
        test_output_dir=Path("/tmp/fsa_examples/tests")
    )

    # Generate FSA
    result = generator.run(spec)

    # Display results
    if result["success"]:
        print(f"\n✓ Successfully generated {result['fsa_name']}")
        print(f"\nGenerated files:")
        for file in result["generated_files"]:
            print(f"  - {file}")
        print(f"\nFinal state: {generator.current_state}")
        print(f"Transitions: {len(generator.transition_history)}")
    else:
        print(f"\n✗ Generation failed: {result['error']}")


def example_fsa_with_methods():
    """Generate an FSA with custom methods."""
    print("\n" + "=" * 60)
    print("Example 2: FSA with Custom Methods")
    print("=" * 60)

    # Create specification with custom methods
    spec = FSASpecification(
        name="APIClientFSA",
        purpose="FSA for managing API client lifecycle",
        states={"initial", "connecting", "authenticated", "ready", "disconnected", "error"},
        methods=[
            {
                "name": "connect",
                "params": [
                    {"name": "url", "type": "str"},
                    {"name": "timeout", "type": "int"}
                ],
                "return_type": "bool",
                "docstring": "Connect to the API endpoint"
            },
            {
                "name": "authenticate",
                "params": [
                    {"name": "api_key", "type": "str"}
                ],
                "return_type": "bool",
                "docstring": "Authenticate with API key"
            },
            {
                "name": "disconnect",
                "params": [],
                "return_type": "None",
                "docstring": "Disconnect from the API"
            }
        ],
        dependencies=["requests", "json"],
        stateful=True,
        custom_transitions=[
            {"from_state": "initial", "to_state": "connecting"},
            {"from_state": "connecting", "to_state": "authenticated"},
            {"from_state": "authenticated", "to_state": "ready"},
            {"from_state": "ready", "to_state": "disconnected"},
            {"from_state": "connecting", "to_state": "error"},
            {"from_state": "authenticated", "to_state": "error"},
        ]
    )

    # Generate FSA
    generator = FSAGeneratorFSA(
        output_dir=Path("/tmp/fsa_examples/generated"),
        test_output_dir=Path("/tmp/fsa_examples/tests")
    )

    result = generator.run(spec)

    if result["success"]:
        print(f"\n✓ Successfully generated {result['fsa_name']}")
        print(f"\nGenerated methods:")
        for method in spec.methods:
            print(f"  - {method['name']}({', '.join(p['name'] for p in method['params'])})")
        print(f"\nGenerated files:")
        for file in result["generated_files"]:
            print(f"  - {file}")


def example_cascade_aware_fsa():
    """Generate a cascade-aware FSA."""
    print("\n" + "=" * 60)
    print("Example 3: Cascade-Aware FSA")
    print("=" * 60)

    spec = FSASpecification(
        name="WorkflowOrchestratorFSA",
        purpose="FSA that can cascade to sub-workflows",
        states={"initial", "planning", "executing", "cascading", "aggregating", "completed", "error"},
        cascade_aware=True,
        stateful=True,
        methods=[
            {
                "name": "plan_workflow",
                "params": [{"name": "config", "type": "Dict[str, Any]"}],
                "return_type": "List[str]",
                "docstring": "Plan the workflow execution steps"
            },
            {
                "name": "execute_step",
                "params": [{"name": "step", "type": "str"}],
                "return_type": "Any",
                "docstring": "Execute a single workflow step"
            },
            {
                "name": "cascade_to_sub_fsa",
                "params": [{"name": "fsa_name", "type": "str"}],
                "return_type": "Any",
                "docstring": "Cascade execution to a sub-FSA"
            },
            {
                "name": "aggregate_results",
                "params": [{"name": "results", "type": "List[Any]"}],
                "return_type": "Dict[str, Any]",
                "docstring": "Aggregate results from all steps"
            }
        ],
        dependencies=["typing"],
        custom_transitions=[
            {"from_state": "initial", "to_state": "planning"},
            {"from_state": "planning", "to_state": "executing"},
            {"from_state": "executing", "to_state": "cascading"},
            {"from_state": "cascading", "to_state": "aggregating"},
            {"from_state": "aggregating", "to_state": "completed"},
            {"from_state": "planning", "to_state": "error"},
            {"from_state": "executing", "to_state": "error"},
            {"from_state": "cascading", "to_state": "error"},
        ]
    )

    generator = FSAGeneratorFSA(
        output_dir=Path("/tmp/fsa_examples/generated"),
        test_output_dir=Path("/tmp/fsa_examples/tests")
    )

    result = generator.run(spec)

    if result["success"]:
        print(f"\n✓ Successfully generated {result['fsa_name']}")
        print(f"  Cascade-aware: {spec.cascade_aware}")
        print(f"  States: {len(spec.states)}")
        print(f"  Methods: {len(spec.methods)}")
        print(f"\nGenerated files:")
        for file in result["generated_files"]:
            print(f"  - {file}")


def example_validation():
    """Demonstrate FSA specification validation."""
    print("\n" + "=" * 60)
    print("Example 4: Specification Validation")
    print("=" * 60)

    # Invalid spec - name doesn't end with FSA
    invalid_spec = FSASpecification(
        name="DataProcessor",
        purpose="Test validation"
    )

    generator = FSAGeneratorFSA()
    result = generator.run(invalid_spec)

    print("\nAttempting to generate FSA with invalid name...")
    if not result["success"]:
        print(f"✓ Validation correctly rejected invalid spec:")
        print(f"  Error: {result['error']}")

    # Valid spec
    valid_spec = FSASpecification(
        name="DataProcessorFSA",
        purpose="Test validation",
        states={"initial", "processing", "completed", "error"}
    )

    result = generator.run(valid_spec)
    print(f"\nValid specification result: {'✓ Success' if result['success'] else '✗ Failed'}")


def example_stateless_fsa():
    """Generate a stateless FSA."""
    print("\n" + "=" * 60)
    print("Example 5: Stateless FSA")
    print("=" * 60)

    spec = FSASpecification(
        name="StatelessValidatorFSA",
        purpose="Stateless FSA for one-time validation tasks",
        states={"initial", "validating", "completed", "error"},
        stateful=False,  # Stateless
        cascade_aware=False,
        methods=[
            {
                "name": "validate_data",
                "params": [{"name": "data", "type": "Any"}],
                "return_type": "bool",
                "docstring": "Validate input data"
            }
        ],
        custom_transitions=[
            {"from_state": "initial", "to_state": "validating"},
            {"from_state": "validating", "to_state": "completed"},
            {"from_state": "validating", "to_state": "error"},
        ]
    )

    generator = FSAGeneratorFSA(
        output_dir=Path("/tmp/fsa_examples/generated"),
        test_output_dir=Path("/tmp/fsa_examples/tests")
    )

    result = generator.run(spec)

    if result["success"]:
        print(f"\n✓ Successfully generated stateless {result['fsa_name']}")
        print(f"  Stateful: {spec.stateful}")
        print(f"  States: {spec.states}")


def example_inspect_generator_state():
    """Inspect FSA Generator state during execution."""
    print("\n" + "=" * 60)
    print("Example 6: Inspecting Generator State")
    print("=" * 60)

    spec = FSASpecification(
        name="SimpleFSA",
        purpose="Simple FSA for state inspection"
    )

    generator = FSAGeneratorFSA(
        output_dir=Path("/tmp/fsa_examples/generated"),
        test_output_dir=Path("/tmp/fsa_examples/tests")
    )

    print(f"\nInitial state: {generator.current_state}")
    print(f"Generator states: {generator.states}")

    result = generator.run(spec)

    if result["success"]:
        print(f"\nFinal state: {generator.current_state}")
        print(f"\nState transition history:")
        for i, trans in enumerate(generator.transition_history, 1):
            print(f"  {i}. {trans['from']} -> {trans['to']}")

        print(f"\nState info:")
        info = generator.get_state_info()
        for key, value in info.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    """Run all examples."""
    print("\n" + "=" * 60)
    print("FSA Generator Examples")
    print("=" * 60)
    print("\nThese examples demonstrate the FSA Generator, a meta-FSA")
    print("that generates new FSA implementations from specifications.")

    # Run examples
    example_basic_fsa_generation()
    example_fsa_with_methods()
    example_cascade_aware_fsa()
    example_validation()
    example_stateless_fsa()
    example_inspect_generator_state()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nGenerated files are in: /tmp/fsa_examples/")
    print("You can inspect the generated FSAs and their tests.")

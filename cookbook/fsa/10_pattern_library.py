"""📚 FSA Pattern Library Example

This example demonstrates using the FSA Pattern Library for reusable
workflow patterns and templates.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.pattern_library import (
    FSAPatternLibrary,
    PatternCategory,
    get_sequential_workflow_pattern,
    get_retry_pattern,
    get_parallel_execution_pattern,
    get_validation_pipeline_pattern,
    get_rollback_pattern
)


def main():
    """Demonstrate FSA Pattern Library"""

    print("\n" + "=" * 60)
    print("FSA PATTERN LIBRARY")
    print("=" * 60)

    # Create pattern library
    library = FSAPatternLibrary(name="PatternLib", debug_mode=True)

    print(f"\n✅ Pattern Library Loaded")
    print(f"Total Patterns: {len(library.patterns)}")

    # List all patterns
    print("\n📚 AVAILABLE PATTERNS:")
    for i, pattern in enumerate(library.list_patterns(), 1):
        print(f"\n{i}. {pattern.name} ({pattern.category.value})")
        print(f"   {pattern.description}")
        print(f"   Use Cases: {', '.join(pattern.use_cases[:2])}...")

    # List patterns by category
    print("\n\n" + "=" * 60)
    print("PATTERNS BY CATEGORY")
    print("=" * 60)

    for category in PatternCategory:
        patterns = library.list_patterns(category=category)
        if patterns:
            print(f"\n## {category.value.upper()} ({len(patterns)} patterns)")
            for pattern in patterns:
                print(f"   - {pattern.name}")

    # Example 1: Sequential Workflow Pattern
    print("\n\n" + "=" * 60)
    print("EXAMPLE 1: SEQUENTIAL WORKFLOW PATTERN")
    print("=" * 60)

    seq_pattern = get_sequential_workflow_pattern()
    print(f"\nPattern: {seq_pattern.name}")
    print(f"Description: {seq_pattern.description}")
    print(f"\nStates: {', '.join(seq_pattern.states)}")
    print(f"\nTransitions:")
    for trans in seq_pattern.transitions:
        print(f"  {trans['from']} → {trans['to']}")
    print(f"\nExample Code:")
    print(seq_pattern.example_code)

    # Example 2: Retry Pattern
    print("\n\n" + "=" * 60)
    print("EXAMPLE 2: RETRY WITH BACKOFF PATTERN")
    print("=" * 60)

    retry_pattern = get_retry_pattern()
    print(f"\nPattern: {retry_pattern.name}")
    print(f"Description: {retry_pattern.description}")
    print(f"\nBest Practices:")
    for i, practice in enumerate(retry_pattern.best_practices, 1):
        print(f"  {i}. {practice}")

    # Example 3: Validation Pipeline
    print("\n\n" + "=" * 60)
    print("EXAMPLE 3: VALIDATION PIPELINE PATTERN")
    print("=" * 60)

    validation_pattern = get_validation_pipeline_pattern()
    print(f"\nPattern: {validation_pattern.name}")
    print(f"\nUse Cases:")
    for i, use_case in enumerate(validation_pattern.use_cases, 1):
        print(f"  {i}. {use_case}")

    # Example 4: Get pattern by name
    print("\n\n" + "=" * 60)
    print("EXAMPLE 4: ACCESSING PATTERNS")
    print("=" * 60)

    pattern = library.get_pattern("parallel_execution")
    if pattern:
        print(f"\nFound Pattern: {pattern.name}")
        print(f"Category: {pattern.category.value}")
        print(f"Description: {pattern.description}")

    # Example 5: Generate Full Catalog
    print("\n\n" + "=" * 60)
    print("FULL PATTERN CATALOG (Preview)")
    print("=" * 60)

    catalog = library.get_pattern_catalog()
    print(catalog[:1500] + "\n...\n[Catalog continues]")

    # Save catalog to file
    catalog_file = "/tmp/fsa_pattern_catalog.md"
    with open(catalog_file, 'w') as f:
        f.write(catalog)
    print(f"\n📄 Full pattern catalog saved to: {catalog_file}")

    # Example 6: Create custom pattern
    print("\n\n" + "=" * 60)
    print("EXAMPLE 6: ADDING CUSTOM PATTERN")
    print("=" * 60)

    from agno.fsa.pattern_library import FSAPattern

    custom_pattern = FSAPattern(
        name="Custom Processing Pipeline",
        category=PatternCategory.WORKFLOW,
        description="Process data through custom stages",
        use_cases=["Custom data processing", "Domain-specific workflows"],
        states=["initial", "processing", "finalizing", "success"],
        transitions=[
            {"from": "initial", "to": "processing"},
            {"from": "processing", "to": "finalizing"},
            {"from": "finalizing", "to": "success"}
        ],
        example_code="# Custom FSA implementation here",
        best_practices=["Define clear stage boundaries", "Add monitoring"]
    )

    library.add_pattern(custom_pattern)
    print(f"\n✅ Added custom pattern: {custom_pattern.name}")
    print(f"Total patterns now: {len(library.patterns)}")


if __name__ == "__main__":
    main()

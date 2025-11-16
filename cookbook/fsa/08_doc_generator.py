"""📚 FSA Documentation Generator Example

This example demonstrates automatic documentation generation from FSA specifications.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.doc_generator import FSADocGenerator, DocumentFormat, DiagramFormat


def main():
    """Demonstrate FSA Documentation Generator"""

    print("\n" + "=" * 60)
    print("FSA DOCUMENTATION GENERATOR")
    print("=" * 60)

    # Create an FSA to document
    code_builder = MultiStepCodeBuilder(
        name="MultiStepCodeBuilder",
        programming_language="python",
        include_tests=True,
        include_documentation=True
    )

    # Create documentation generator
    doc_gen = FSADocGenerator(
        name="DocGenerator",
        output_format=DocumentFormat.MARKDOWN,
        diagram_format=DiagramFormat.MERMAID,
        include_examples=True,
        include_api_reference=True,
        include_troubleshooting=True,
        debug_mode=True
    )

    # Generate documentation
    result = doc_gen.run({"fsa": code_builder})

    print(f"\n✅ Documentation Generated!")
    print(f"Format: {result.format.value}")
    print(f"Generated at: {result.generated_at}")
    print(f"Sections: {len(result.sections)}")

    # Display state diagram
    print("\n" + "=" * 60)
    print("STATE DIAGRAM (Mermaid)")
    print("=" * 60)
    print(result.state_diagram)

    # Display transition table preview
    print("\n" + "=" * 60)
    print("TRANSITION TABLE (Preview)")
    print("=" * 60)
    print(result.transition_table[:500] + "..." if len(result.transition_table) > 500 else result.transition_table)

    # Show sections
    print("\n" + "=" * 60)
    print("DOCUMENTATION SECTIONS")
    print("=" * 60)
    for i, section in enumerate(result.sections, 1):
        print(f"{i}. {section.title}")

    # Save full documentation
    output_file = "/tmp/fsa_documentation.md"
    with open(output_file, 'w') as f:
        f.write(result.full_document)

    print(f"\n📄 Full documentation saved to: {output_file}")
    print(f"   Size: {len(result.full_document)} characters")

    # Show preview of full document
    print("\n" + "=" * 60)
    print("FULL DOCUMENT PREVIEW (First 1000 chars)")
    print("=" * 60)
    print(result.full_document[:1000])
    print("...\n[Document continues]")


if __name__ == "__main__":
    main()

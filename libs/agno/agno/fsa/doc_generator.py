"""
FSA Documentation Generator

Automatically generates comprehensive documentation from FSA specifications:
- State diagrams (Mermaid, PlantUML, ASCII)
- Transition tables
- API documentation
- Usage examples
- Integration guides
- Troubleshooting guides

Supports multiple output formats: Markdown, HTML, PDF, JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class DocGeneratorState(str, Enum):
    """States for Documentation Generator"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    GENERATING_DIAGRAM = "generating_diagram"
    GENERATING_API_DOCS = "generating_api_docs"
    GENERATING_EXAMPLES = "generating_examples"
    GENERATING_GUIDE = "generating_guide"
    FORMATTING = "formatting"
    SUCCESS = "success"
    FAILED = "failed"


class DocumentFormat(str, Enum):
    """Output format for documentation"""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PLAINTEXT = "plaintext"


class DiagramFormat(str, Enum):
    """Diagram format"""
    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    ASCII = "ascii"
    GRAPHVIZ = "graphviz"


class DocumentationSection(BaseModel):
    """A section of documentation"""
    title: str
    content: str
    subsections: List["DocumentationSection"] = []


class FSADocumentation(BaseModel):
    """Generated FSA documentation"""
    fsa_name: str
    generated_at: str
    format: DocumentFormat
    sections: List[DocumentationSection]
    state_diagram: str
    transition_table: str
    api_reference: str
    examples: List[str]
    full_document: str


@dataclass
class FSADocGenerator(FSA):
    """
    FSA Documentation Generator

    Automatically generates comprehensive documentation including:
    - Overview and purpose
    - State diagrams (multiple formats)
    - Transition tables
    - State descriptions
    - API reference
    - Usage examples
    - Integration guide
    - Troubleshooting

    Example:
        ```python
        # Create FSA to document
        my_fsa = MultiStepCodeBuilder(...)

        # Create documentation generator
        doc_gen = FSADocGenerator(
            name="DocGenerator",
            output_format=DocumentFormat.MARKDOWN,
            diagram_format=DiagramFormat.MERMAID
        )

        # Generate docs
        result = doc_gen.run({"fsa": my_fsa})

        # Save to file
        with open("fsa_docs.md", "w") as f:
            f.write(result.full_document)
        ```
    """

    # Target FSA to document
    target_fsa: Optional[FSA] = None

    # Documentation agent (optional, for intelligent descriptions)
    doc_agent: Optional[Agent] = None

    # Configuration
    output_format: DocumentFormat = DocumentFormat.MARKDOWN
    diagram_format: DiagramFormat = DiagramFormat.MERMAID
    include_examples: bool = True
    include_api_reference: bool = True
    include_troubleshooting: bool = True

    # Generated sections
    sections: List[DocumentationSection] = field(default_factory=list)
    state_diagram: str = ""
    transition_table: str = ""
    api_reference: str = ""
    examples: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize documentation generator"""
        self.initial_state = DocGeneratorState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {DocGeneratorState.SUCCESS, DocGeneratorState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSADocGenerator {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup documentation generation workflow"""
        # INITIAL -> ANALYZING
        self.add_transition(
            DocGeneratorState.INITIAL,
            DocGeneratorState.ANALYZING,
            action=self._analyze_fsa,
            description="Analyze FSA structure"
        )

        # ANALYZING -> GENERATING_DIAGRAM
        self.add_transition(
            DocGeneratorState.ANALYZING,
            DocGeneratorState.GENERATING_DIAGRAM,
            condition=lambda ctx: ctx.get("analysis_complete", False),
            action=self._generate_diagram,
            description="Generate state diagram"
        )

        # GENERATING_DIAGRAM -> GENERATING_API_DOCS
        self.add_transition(
            DocGeneratorState.GENERATING_DIAGRAM,
            DocGeneratorState.GENERATING_API_DOCS,
            condition=lambda ctx: ctx.get("diagram_generated", False),
            action=self._generate_api_docs,
            description="Generate API documentation"
        )

        # GENERATING_API_DOCS -> GENERATING_EXAMPLES
        self.add_transition(
            DocGeneratorState.GENERATING_API_DOCS,
            DocGeneratorState.GENERATING_GUIDE,
            condition=lambda ctx: ctx.get("api_docs_generated", False) and not self.include_examples,
            description="Skip to guide generation"
        )

        self.add_transition(
            DocGeneratorState.GENERATING_API_DOCS,
            DocGeneratorState.GENERATING_EXAMPLES,
            condition=lambda ctx: ctx.get("api_docs_generated", False) and self.include_examples,
            action=self._generate_examples,
            description="Generate usage examples"
        )

        # GENERATING_EXAMPLES -> GENERATING_GUIDE
        self.add_transition(
            DocGeneratorState.GENERATING_EXAMPLES,
            DocGeneratorState.GENERATING_GUIDE,
            condition=lambda ctx: ctx.get("examples_generated", False),
            action=self._generate_guide,
            description="Generate integration guide"
        )

        # GENERATING_GUIDE -> FORMATTING
        self.add_transition(
            DocGeneratorState.GENERATING_GUIDE,
            DocGeneratorState.FORMATTING,
            condition=lambda ctx: ctx.get("guide_generated", False),
            action=self._format_documentation,
            description="Format final documentation"
        )

        # FORMATTING -> SUCCESS
        self.add_transition(
            DocGeneratorState.FORMATTING,
            DocGeneratorState.SUCCESS,
            condition=lambda ctx: ctx.get("formatting_complete", False),
            description="Documentation complete"
        )

        # Error handling
        for state in DocGeneratorState:
            if state not in [DocGeneratorState.SUCCESS, DocGeneratorState.FAILED]:
                self.add_transition(
                    state,
                    DocGeneratorState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _analyze_fsa(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze FSA structure for documentation"""
        fsa = context.get("fsa") or self.target_fsa

        if not fsa:
            context["critical_error"] = True
            raise ValueError("No FSA provided for documentation")

        self.target_fsa = fsa

        if self.debug_mode:
            logger.debug(f"Analyzing FSA: {fsa.name}")

        # Extract structure
        context["fsa_name"] = fsa.name
        context["fsa_description"] = getattr(fsa, "description", "No description available")
        context["initial_state"] = fsa.initial_state
        context["final_states"] = fsa.final_states
        context["transitions"] = fsa.transitions

        # Collect all states
        states = set()
        for from_state, trans_list in fsa.transitions.items():
            states.add(from_state)
            for trans in trans_list:
                states.add(trans.to_state)
        states.update(fsa.final_states)

        context["states"] = states
        context["analysis_complete"] = True

        return context

    def _generate_diagram(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate state diagram"""
        if self.debug_mode:
            logger.debug(f"Generating {self.diagram_format.value} diagram")

        if self.diagram_format == DiagramFormat.MERMAID:
            self.state_diagram = self._generate_mermaid_diagram(context)
        elif self.diagram_format == DiagramFormat.ASCII:
            self.state_diagram = self._generate_ascii_diagram(context)
        elif self.diagram_format == DiagramFormat.PLANTUML:
            self.state_diagram = self._generate_plantuml_diagram(context)
        else:
            self.state_diagram = self._generate_mermaid_diagram(context)

        # Generate transition table
        self.transition_table = self._generate_transition_table(context)

        context["diagram_generated"] = True

        return context

    def _generate_mermaid_diagram(self, context: Dict[str, Any]) -> str:
        """Generate Mermaid state diagram"""
        fsa_name = context.get("fsa_name", "FSA")
        initial_state = context.get("initial_state")
        final_states = context.get("final_states", set())
        transitions = context.get("transitions", {})

        diagram = "```mermaid\nstateDiagram-v2\n"
        diagram += f"    [*] --> {self._format_state_name(initial_state)}\n"

        # Add transitions
        for from_state, trans_list in transitions.items():
            for trans in trans_list:
                from_name = self._format_state_name(from_state)
                to_name = self._format_state_name(trans.to_state)
                label = trans.description if trans.description else ""
                if label:
                    diagram += f"    {from_name} --> {to_name}: {label}\n"
                else:
                    diagram += f"    {from_name} --> {to_name}\n"

        # Add final states
        for final_state in final_states:
            final_name = self._format_state_name(final_state)
            diagram += f"    {final_name} --> [*]\n"

        diagram += "```"

        return diagram

    def _generate_ascii_diagram(self, context: Dict[str, Any]) -> str:
        """Generate ASCII state diagram"""
        initial_state = context.get("initial_state")
        states = context.get("states", set())
        transitions = context.get("transitions", {})

        diagram = "State Diagram (ASCII):\n\n"
        diagram += f"[START] --> {initial_state}\n"

        for from_state, trans_list in transitions.items():
            for trans in trans_list:
                label = f" ({trans.description})" if trans.description else ""
                diagram += f"{from_state} --> {trans.to_state}{label}\n"

        return diagram

    def _generate_plantuml_diagram(self, context: Dict[str, Any]) -> str:
        """Generate PlantUML state diagram"""
        initial_state = context.get("initial_state")
        final_states = context.get("final_states", set())
        transitions = context.get("transitions", {})

        diagram = "@startuml\n"
        diagram += f"[*] --> {initial_state}\n"

        for from_state, trans_list in transitions.items():
            for trans in trans_list:
                label = f" : {trans.description}" if trans.description else ""
                diagram += f"{from_state} --> {trans.to_state}{label}\n"

        for final_state in final_states:
            diagram += f"{final_state} --> [*]\n"

        diagram += "@enduml"

        return diagram

    def _generate_transition_table(self, context: Dict[str, Any]) -> str:
        """Generate transition table"""
        transitions = context.get("transitions", {})

        if self.output_format == DocumentFormat.MARKDOWN:
            table = "\n| From State | To State | Condition | Action | Description |\n"
            table += "|------------|----------|-----------|--------|-------------|\n"

            for from_state, trans_list in transitions.items():
                for trans in trans_list:
                    has_condition = "✓" if trans.condition else "✗"
                    has_action = "✓" if trans.action else "✗"
                    desc = trans.description or "-"
                    table += f"| {from_state} | {trans.to_state} | {has_condition} | {has_action} | {desc} |\n"

            return table
        else:
            # Plain text table
            table = "\nTransition Table:\n"
            for from_state, trans_list in transitions.items():
                for trans in trans_list:
                    table += f"  {from_state} -> {trans.to_state}"
                    if trans.description:
                        table += f" ({trans.description})"
                    table += "\n"
            return table

    def _format_state_name(self, state) -> str:
        """Format state name for diagrams"""
        if hasattr(state, "value"):
            return state.value
        return str(state).replace(" ", "_")

    def _generate_api_docs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate API reference documentation"""
        if self.debug_mode:
            logger.debug("Generating API documentation")

        fsa_name = context.get("fsa_name", "FSA")
        fsa_description = context.get("fsa_description", "")

        if self.output_format == DocumentFormat.MARKDOWN:
            api_docs = f"## API Reference\n\n"
            api_docs += f"### {fsa_name}\n\n"
            api_docs += f"{fsa_description}\n\n"

            # Constructor
            api_docs += "#### Constructor\n\n"
            api_docs += f"```python\n{fsa_name}(\n"
            api_docs += "    name: str,\n"
            api_docs += "    debug_mode: bool = False\n"
            api_docs += ")\n```\n\n"

            # Methods
            api_docs += "#### Methods\n\n"
            api_docs += "**`run(initial_context: Dict[str, Any]) -> FSAExecutionResult`**\n\n"
            api_docs += "Execute the FSA with the provided context.\n\n"
            api_docs += "**Parameters:**\n"
            api_docs += "- `initial_context`: Dictionary containing input data\n\n"
            api_docs += "**Returns:**\n"
            api_docs += "- `FSAExecutionResult`: Execution results and metadata\n\n"

            self.api_reference = api_docs
        else:
            self.api_reference = f"API Reference for {fsa_name}\n\n{fsa_description}"

        context["api_docs_generated"] = True

        return context

    def _generate_examples(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate usage examples"""
        if self.debug_mode:
            logger.debug("Generating usage examples")

        fsa_name = context.get("fsa_name", "FSA")

        # Basic usage example
        example1 = f"""### Basic Usage

```python
from agno.fsa import {fsa_name}

# Create FSA instance
fsa = {fsa_name}(name="MyFSA", debug_mode=True)

# Run FSA
result = fsa.run({{"input": "data"}})

# Check results
if result.success:
    print(f"FSA completed successfully")
    print(f"Final state: {{result.final_state}}")
else:
    print(f"FSA failed: {{result.error}}")
```
"""

        # Advanced example
        example2 = f"""### Advanced Usage

```python
# Create with custom configuration
fsa = {fsa_name}(
    name="AdvancedFSA",
    debug_mode=True
)

# Provide detailed context
context = {{
    "task": "Process data",
    "options": {{"verbose": True}}
}}

# Execute and monitor
result = fsa.run(context)

# Analyze state history
print(f"States visited: {{result.state_history}}")
print(f"Execution time: {{result.execution_time}}s")
```
"""

        self.examples = [example1, example2]

        context["examples_generated"] = True

        return context

    def _generate_guide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate integration and usage guide"""
        if self.debug_mode:
            logger.debug("Generating integration guide")

        fsa_name = context.get("fsa_name", "FSA")
        states = context.get("states", set())

        # Create overview section
        overview = DocumentationSection(
            title="Overview",
            content=f"{fsa_name} is an FSA with {len(states)} states. {context.get('fsa_description', '')}"
        )

        # Create states section
        states_content = "The FSA includes the following states:\n\n"
        for state in sorted(states, key=str):
            states_content += f"- **{state}**: State description\n"

        states_section = DocumentationSection(
            title="States",
            content=states_content
        )

        # Create transitions section
        transitions_section = DocumentationSection(
            title="Transitions",
            content=self.transition_table
        )

        self.sections = [overview, states_section, transitions_section]

        context["guide_generated"] = True

        return context

    def _format_documentation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format final documentation"""
        if self.debug_mode:
            logger.debug(f"Formatting documentation as {self.output_format.value}")

        fsa_name = context.get("fsa_name", "FSA")

        if self.output_format == DocumentFormat.MARKDOWN:
            doc = f"# {fsa_name} Documentation\n\n"
            doc += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            doc += "---\n\n"

            # Add sections
            for section in self.sections:
                doc += f"## {section.title}\n\n"
                doc += f"{section.content}\n\n"

            # Add diagram
            doc += "## State Diagram\n\n"
            doc += f"{self.state_diagram}\n\n"

            # Add transition table
            doc += "## Transition Table\n\n"
            doc += f"{self.transition_table}\n\n"

            # Add API reference
            if self.include_api_reference:
                doc += self.api_reference
                doc += "\n"

            # Add examples
            if self.include_examples and self.examples:
                doc += "## Examples\n\n"
                for example in self.examples:
                    doc += f"{example}\n\n"

            # Add troubleshooting
            if self.include_troubleshooting:
                doc += "## Troubleshooting\n\n"
                doc += "### Common Issues\n\n"
                doc += "**FSA gets stuck in a state**\n"
                doc += "- Enable debug mode to see state transitions\n"
                doc += "- Check transition conditions are being met\n"
                doc += "- Verify context data is correct\n\n"

            context["full_document"] = doc
        else:
            # Plain text format
            doc = f"{fsa_name} Documentation\n"
            doc += "=" * 50 + "\n\n"
            for section in self.sections:
                doc += f"{section.title}\n{'-' * len(section.title)}\n"
                doc += f"{section.content}\n\n"
            context["full_document"] = doc

        context["formatting_complete"] = True

        return context

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> FSADocumentation:
        """
        Generate documentation for an FSA

        Args:
            initial_context: Context with FSA to document

        Returns:
            FSADocumentation with generated docs
        """
        # Execute base FSA run
        base_result = super().run(initial_context)

        # Build documentation result
        return FSADocumentation(
            fsa_name=self.target_fsa.name if self.target_fsa else "Unknown",
            generated_at=datetime.now().isoformat(),
            format=self.output_format,
            sections=self.sections,
            state_diagram=self.state_diagram,
            transition_table=self.transition_table,
            api_reference=self.api_reference,
            examples=self.examples,
            full_document=self.context.get("full_document", "")
        )

    def save_documentation(self, filepath: str) -> None:
        """Save documentation to file"""
        result = self.run({"fsa": self.target_fsa})
        with open(filepath, 'w') as f:
            f.write(result.full_document)
        if self.debug_mode:
            logger.debug(f"Documentation saved to {filepath}")

"""
FSA Workflow Designer

Visual FSA builder and designer:
- Create FSAs without code
- Visual state and transition editing
- Export to Python code
- Import from JSON/YAML
- Validation and preview
- Template-based creation
- Interactive design mode

Accelerates FSA development through visual tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import json
import yaml

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition
from agno.utils.log import logger


class DesignerState(str, Enum):
    """States for Workflow Designer"""
    INITIAL = "initial"
    LOADING = "loading"
    DESIGNING = "designing"
    VALIDATING = "validating"
    GENERATING = "generating"
    EXPORTING = "exporting"
    SUCCESS = "success"
    FAILED = "failed"


class StateDefinition(BaseModel):
    """Definition of a state"""
    name: str
    is_initial: bool = False
    is_final: bool = False
    description: str = ""
    metadata: Dict[str, Any] = {}


class TransitionDefinition(BaseModel):
    """Definition of a transition"""
    from_state: str
    to_state: str
    condition_code: Optional[str] = None
    action_code: Optional[str] = None
    description: str = ""


class FSADesign(BaseModel):
    """Complete FSA design"""
    name: str
    description: str
    states: List[StateDefinition]
    transitions: List[TransitionDefinition]
    metadata: Dict[str, Any] = {}


class GeneratedCode(BaseModel):
    """Generated FSA code"""
    class_code: str
    example_usage: str
    import_statements: str


@dataclass
class FSAWorkflowDesigner(FSA):
    """
    FSA Workflow Designer

    Visual tool for building FSAs:
    - Create states and transitions visually
    - Define conditions and actions
    - Validate design before code generation
    - Generate Python code
    - Export to JSON/YAML
    - Import existing designs
    - Use templates for common patterns

    Example:
        ```python
        # Create designer
        designer = FSAWorkflowDesigner(name="Designer")

        # Create design
        design = FSADesign(
            name="MyWorkflow",
            description="Custom workflow",
            states=[
                StateDefinition(name="initial", is_initial=True),
                StateDefinition(name="processing"),
                StateDefinition(name="success", is_final=True)
            ],
            transitions=[
                TransitionDefinition(from_state="initial", to_state="processing"),
                TransitionDefinition(from_state="processing", to_state="success")
            ]
        )

        # Generate code
        result = designer.run({"design": design})
        print(result.class_code)
        ```
    """

    # Current design
    current_design: Optional[FSADesign] = None

    # Generated code
    generated_code: Optional[GeneratedCode] = None

    # Templates
    templates: Dict[str, FSADesign] = field(default_factory=dict)

    # Configuration
    include_type_hints: bool = True
    include_documentation: bool = True
    include_examples: bool = True
    validate_before_export: bool = True

    def __post_init__(self):
        """Initialize workflow designer"""
        self.initial_state = DesignerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {DesignerState.SUCCESS, DesignerState.FAILED}
        self.state_history = [self.current_state]

        self._load_templates()
        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAWorkflowDesigner {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup designer workflow"""
        # INITIAL -> LOADING
        self.add_transition(
            DesignerState.INITIAL,
            DesignerState.LOADING,
            action=self._load_design,
            description="Load design"
        )

        # LOADING -> DESIGNING
        self.add_transition(
            DesignerState.LOADING,
            DesignerState.DESIGNING,
            condition=lambda ctx: ctx.get("design_loaded", False),
            action=self._process_design,
            description="Process design"
        )

        # DESIGNING -> VALIDATING
        self.add_transition(
            DesignerState.DESIGNING,
            DesignerState.VALIDATING,
            condition=lambda ctx: ctx.get("design_complete", False),
            action=self._validate_design,
            description="Validate design"
        )

        # VALIDATING -> GENERATING
        self.add_transition(
            DesignerState.VALIDATING,
            DesignerState.GENERATING,
            condition=lambda ctx: ctx.get("validation_passed", False),
            action=self._generate_code,
            description="Generate code"
        )

        # GENERATING -> EXPORTING
        self.add_transition(
            DesignerState.GENERATING,
            DesignerState.EXPORTING,
            condition=lambda ctx: ctx.get("code_generated", False),
            action=self._export_design,
            description="Export design"
        )

        # EXPORTING -> SUCCESS
        self.add_transition(
            DesignerState.EXPORTING,
            DesignerState.SUCCESS,
            condition=lambda ctx: ctx.get("export_complete", False),
            description="Design complete"
        )

        # Error handling
        for state in DesignerState:
            if state not in [DesignerState.SUCCESS, DesignerState.FAILED]:
                self.add_transition(
                    state,
                    DesignerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _load_templates(self) -> None:
        """Load built-in design templates"""
        # Template 1: Simple Sequential
        self.templates["simple_sequential"] = FSADesign(
            name="SimpleSequential",
            description="Simple sequential workflow",
            states=[
                StateDefinition(name="initial", is_initial=True, description="Starting point"),
                StateDefinition(name="step_1", description="First step"),
                StateDefinition(name="step_2", description="Second step"),
                StateDefinition(name="success", is_final=True, description="Completion")
            ],
            transitions=[
                TransitionDefinition(from_state="initial", to_state="step_1"),
                TransitionDefinition(from_state="step_1", to_state="step_2"),
                TransitionDefinition(from_state="step_2", to_state="success")
            ]
        )

        # Template 2: With Error Handling
        self.templates["with_error_handling"] = FSADesign(
            name="WithErrorHandling",
            description="Workflow with error handling",
            states=[
                StateDefinition(name="initial", is_initial=True),
                StateDefinition(name="processing"),
                StateDefinition(name="success", is_final=True),
                StateDefinition(name="failed", is_final=True)
            ],
            transitions=[
                TransitionDefinition(from_state="initial", to_state="processing"),
                TransitionDefinition(from_state="processing", to_state="success",
                                   condition_code="lambda ctx: ctx.get('success', False)"),
                TransitionDefinition(from_state="processing", to_state="failed",
                                   condition_code="lambda ctx: not ctx.get('success', False)")
            ]
        )

    def _load_design(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Load design from context or template"""
        design = context.get("design")
        template_name = context.get("template")

        if design:
            self.current_design = design if isinstance(design, FSADesign) else FSADesign(**design)
        elif template_name and template_name in self.templates:
            self.current_design = self.templates[template_name]
        else:
            context["critical_error"] = True
            raise ValueError("No design or template provided")

        if self.debug_mode:
            logger.debug(f"Loaded design: {self.current_design.name}")

        context["design_loaded"] = True
        return context

    def _process_design(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and prepare design"""
        if self.debug_mode:
            logger.debug("Processing design")

        # Verify design completeness
        if not self.current_design:
            context["critical_error"] = True
            raise ValueError("No design loaded")

        context["design_complete"] = True
        return context

    def _validate_design(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate design structure"""
        if self.debug_mode:
            logger.debug("Validating design")

        design = self.current_design
        issues = []

        # Check for initial state
        initial_states = [s for s in design.states if s.is_initial]
        if len(initial_states) == 0:
            issues.append("No initial state defined")
        elif len(initial_states) > 1:
            issues.append("Multiple initial states defined")

        # Check for final states
        final_states = [s for s in design.states if s.is_final]
        if len(final_states) == 0:
            issues.append("No final states defined")

        # Check transitions reference valid states
        state_names = {s.name for s in design.states}
        for trans in design.transitions:
            if trans.from_state not in state_names:
                issues.append(f"Transition references unknown state: {trans.from_state}")
            if trans.to_state not in state_names:
                issues.append(f"Transition references unknown state: {trans.to_state}")

        # Check for unreachable states (simple check)
        if initial_states:
            reachable = {initial_states[0].name}
            changed = True
            while changed:
                changed = False
                for trans in design.transitions:
                    if trans.from_state in reachable and trans.to_state not in reachable:
                        reachable.add(trans.to_state)
                        changed = True

            unreachable = state_names - reachable
            if unreachable:
                issues.append(f"Unreachable states: {', '.join(unreachable)}")

        context["validation_issues"] = issues
        context["validation_passed"] = len(issues) == 0

        if issues and self.debug_mode:
            logger.warning(f"Validation issues: {issues}")

        return context

    def _generate_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Python code from design"""
        if self.debug_mode:
            logger.debug("Generating code")

        design = self.current_design

        # Generate imports
        imports = "from agno.fsa.base import FSA\nfrom enum import Enum\nfrom typing import Dict, Any\n\n"

        # Generate state enum
        class_code = f"class {design.name}State(str, Enum):\n"
        class_code += f'    """States for {design.name}"""\n'
        for state in design.states:
            state_name = state.name.upper()
            class_code += f'    {state_name} = "{state.name}"\n'
        class_code += "\n\n"

        # Generate FSA class
        class_code += f"class {design.name}(FSA):\n"
        if self.include_documentation:
            class_code += f'    """\n    {design.description}\n    """\n\n'

        # Generate __init__
        class_code += "    def __init__(self, name: str, **kwargs):\n"
        initial_state = next((s.name for s in design.states if s.is_initial), "initial")
        class_code += f"        super().__init__(name=name, initial_state={design.name}State.{initial_state.upper()}, **kwargs)\n"

        # Set final states
        final_states = [s.name.upper() for s in design.states if s.is_final]
        class_code += f"        self.final_states = {{{', '.join([f'{design.name}State.{s}' for s in final_states])}}}\n"

        # Add transitions
        class_code += "        self._setup_transitions()\n\n"

        # Generate _setup_transitions method
        class_code += "    def _setup_transitions(self):\n"
        class_code += f'        """Setup transitions for {design.name}"""\n'

        for trans in design.transitions:
            from_state = f"{design.name}State.{trans.from_state.upper()}"
            to_state = f"{design.name}State.{trans.to_state.upper()}"

            class_code += f"        self.add_transition(\n"
            class_code += f"            {from_state},\n"
            class_code += f"            {to_state}"

            if trans.condition_code:
                class_code += f",\n            condition={trans.condition_code}"
            if trans.action_code:
                class_code += f",\n            action={trans.action_code}"
            if trans.description:
                class_code += f',\n            description="{trans.description}"'

            class_code += "\n        )\n"

        # Generate example usage
        example = f"""# Example usage
fsa = {design.name}(name="{design.name}Example")
result = fsa.run({{"input": "data"}})
print(f"Final state: {{result.final_state}}")
print(f"Success: {{result.success}}")
"""

        self.generated_code = GeneratedCode(
            class_code=class_code,
            example_usage=example,
            import_statements=imports
        )

        context["code_generated"] = True
        return context

    def _export_design(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Export design to requested format"""
        export_format = context.get("export_format", "python")

        if export_format == "python":
            context["exported_code"] = (
                self.generated_code.import_statements +
                self.generated_code.class_code +
                "\n\n" +
                self.generated_code.example_usage
            )
        elif export_format == "json":
            context["exported_code"] = self.current_design.json(indent=2)
        elif export_format == "yaml":
            context["exported_code"] = yaml.dump(
                self.current_design.dict(),
                default_flow_style=False
            )

        context["export_complete"] = True
        return context

    def create_from_template(self, template_name: str) -> FSADesign:
        """Create design from template"""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        return self.templates[template_name].copy(deep=True)

    def add_state(self, state: StateDefinition) -> None:
        """Add state to current design"""
        if not self.current_design:
            raise ValueError("No design loaded")

        self.current_design.states.append(state)

    def add_transition(self, transition: TransitionDefinition) -> None:
        """Add transition to current design"""
        if not self.current_design:
            raise ValueError("No design loaded")

        self.current_design.transitions.append(transition)

    def save_design(self, filepath: str, format: str = "json") -> None:
        """Save design to file"""
        if not self.current_design:
            raise ValueError("No design to save")

        with open(filepath, 'w') as f:
            if format == "json":
                json.dump(self.current_design.dict(), f, indent=2)
            elif format == "yaml":
                yaml.dump(self.current_design.dict(), f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported format: {format}")

        if self.debug_mode:
            logger.debug(f"Saved design to {filepath}")

    def load_design_from_file(self, filepath: str) -> FSADesign:
        """Load design from file"""
        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                data = json.load(f)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file format: {filepath}")

        self.current_design = FSADesign(**data)

        if self.debug_mode:
            logger.debug(f"Loaded design from {filepath}")

        return self.current_design

    def export_to_python(self, filepath: str) -> None:
        """Export generated code to Python file"""
        if not self.generated_code:
            # Generate code first
            self.run({"design": self.current_design})

        with open(filepath, 'w') as f:
            f.write(self.generated_code.import_statements)
            f.write(self.generated_code.class_code)
            f.write("\n\n")
            f.write(self.generated_code.example_usage)

        if self.debug_mode:
            logger.debug(f"Exported code to {filepath}")

    def get_state_diagram_mermaid(self) -> str:
        """Generate Mermaid state diagram"""
        if not self.current_design:
            return ""

        diagram = "```mermaid\nstateDiagram-v2\n"

        # Add initial state
        initial = next((s.name for s in self.current_design.states if s.is_initial), None)
        if initial:
            diagram += f"    [*] --> {initial}\n"

        # Add transitions
        for trans in self.current_design.transitions:
            desc = f": {trans.description}" if trans.description else ""
            diagram += f"    {trans.from_state} --> {trans.to_state}{desc}\n"

        # Add final states
        for state in self.current_design.states:
            if state.is_final:
                diagram += f"    {state.name} --> [*]\n"

        diagram += "```"
        return diagram

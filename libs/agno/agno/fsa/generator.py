"""FSA Generator - A meta-level FSA that generates other FSA code files."""

from typing import Dict, List, Optional, Any


class FSAGenerator:
    """
    A Finite State Automaton that generates code for other FSAs.

    States: parse_spec → validate → generate_structure → add_logic → complete

    Purpose: Takes FSA specifications and outputs complete FSA Python code.
    """

    def __init__(self):
        self.state = "parse_spec"
        self.fsa_name: Optional[str] = None
        self.states_list: List[str] = []
        self.transitions_dict: Dict[tuple, str] = {}
        self.purpose_description: Optional[str] = None
        self.generated_code: str = ""
        self.errors: List[str] = []

    def generate(
        self,
        fsa_name: str,
        states_list: List[str],
        transitions_dict: Dict[tuple, str],
        purpose_description: str
    ) -> str:
        """
        Generate complete FSA code from specifications.

        Args:
            fsa_name: Name of the FSA class to generate
            states_list: List of state names for the FSA
            transitions_dict: Dictionary mapping (current_state, input_symbol) -> next_state
            purpose_description: Description of the FSA's purpose

        Returns:
            Complete Python code as a string

        Raises:
            ValueError: If specifications are invalid
        """
        self.state = "parse_spec"
        self._parse_spec(fsa_name, states_list, transitions_dict, purpose_description)

        self.state = "validate"
        self._validate()

        if self.errors:
            raise ValueError(f"Invalid FSA specification: {', '.join(self.errors)}")

        self.state = "generate_structure"
        self._generate_structure()

        self.state = "add_logic"
        self._add_logic()

        self.state = "complete"
        return self.generated_code

    def _parse_spec(
        self,
        fsa_name: str,
        states_list: List[str],
        transitions_dict: Dict[tuple, str],
        purpose_description: str
    ) -> None:
        """Parse the FSA specification."""
        self.fsa_name = fsa_name
        self.states_list = states_list
        self.transitions_dict = transitions_dict
        self.purpose_description = purpose_description
        self.errors = []

    def _validate(self) -> None:
        """Validate the FSA specification."""
        # Validate FSA name
        if not self.fsa_name or not self.fsa_name.isidentifier():
            self.errors.append("fsa_name must be a valid Python identifier")

        # Validate states list
        if not self.states_list:
            self.errors.append("states_list cannot be empty")

        if not all(isinstance(s, str) and s.isidentifier() for s in self.states_list):
            self.errors.append("All states must be valid Python identifiers")

        # Validate transitions
        if not isinstance(self.transitions_dict, dict):
            self.errors.append("transitions_dict must be a dictionary")
            return

        for (state, input_symbol), next_state in self.transitions_dict.items():
            if state not in self.states_list:
                self.errors.append(f"Transition source state '{state}' not in states_list")
            if next_state not in self.states_list:
                self.errors.append(f"Transition target state '{next_state}' not in states_list")

    def _generate_structure(self) -> None:
        """Generate the basic FSA class structure."""
        code_lines = [
            '"""Generated FSA code."""',
            "",
            "from typing import Dict, List, Optional, Any",
            "",
            "",
            f"class {self.fsa_name}:",
            f'    """',
            f"    {self.purpose_description}",
            f'    """',
            "",
            "    def __init__(self):",
            f'        self.state = "{self.states_list[0]}"  # Initial state',
            f"        self.states = {self.states_list}",
            f"        self.transitions = {self._format_transitions()}",
            "        self.history: List[str] = []",
            "",
        ]
        self.generated_code = "\n".join(code_lines)

    def _format_transitions(self) -> str:
        """Format transitions dictionary for code generation."""
        lines = ["{"]
        for (state, input_symbol), next_state in self.transitions_dict.items():
            lines.append(f'            ("{state}", "{input_symbol}"): "{next_state}",')
        lines.append("        }")
        return "\n".join(lines)

    def _add_logic(self) -> None:
        """Add FSA logic methods."""
        methods = [
            "    def transition(self, input_symbol: str) -> bool:",
            '        """',
            "        Perform a state transition based on input.",
            "        ",
            "        Args:",
            "            input_symbol: Input symbol to trigger transition",
            "            ",
            "        Returns:",
            "            True if transition was successful, False otherwise",
            '        """',
            "        key = (self.state, input_symbol)",
            "        if key in self.transitions:",
            "            self.history.append(self.state)",
            "            self.state = self.transitions[key]",
            "            return True",
            "        return False",
            "",
            "    def reset(self) -> None:",
            '        """Reset FSA to initial state."""',
            f'        self.state = "{self.states_list[0]}"',
            "        self.history = []",
            "",
            "    def get_state(self) -> str:",
            '        """Get current state."""',
            "        return self.state",
            "",
            "    def get_history(self) -> List[str]:",
            '        """Get state transition history."""',
            "        return self.history.copy()",
            "",
            "    def is_valid_transition(self, input_symbol: str) -> bool:",
            '        """Check if transition is valid from current state."""',
            "        return (self.state, input_symbol) in self.transitions",
            "",
            "    def get_available_transitions(self) -> List[str]:",
            '        """Get all available input symbols from current state."""',
            "        return [",
            "            input_sym",
            "            for (state, input_sym) in self.transitions.keys()",
            "            if state == self.state",
            "        ]",
            "",
            "    def run(self, inputs: List[str]) -> Dict[str, Any]:",
            '        """',
            "        Run FSA with sequence of inputs.",
            "        ",
            "        Args:",
            "            inputs: List of input symbols",
            "            ",
            "        Returns:",
            "            Dictionary with final state, success status, and history",
            '        """',
            "        self.reset()",
            "        success = True",
            "        ",
            "        for input_symbol in inputs:",
            "            if not self.transition(input_symbol):",
            "                success = False",
            "                break",
            "        ",
            "        return {",
            '            "final_state": self.state,',
            '            "success": success,',
            '            "history": self.get_history(),',
            "        }",
        ]

        self.generated_code += "\n".join(methods) + "\n"

    def save_to_file(self, output_path: str) -> None:
        """
        Save generated FSA code to a file.

        Args:
            output_path: Path where the generated code should be saved
        """
        with open(output_path, "w") as f:
            f.write(self.generated_code)

# FSA Generator

A meta-level Finite State Automaton that generates code for other FSAs.

## Overview

The FSA Generator is itself an FSA with the following states:
- `parse_spec` - Parse input specifications
- `validate` - Validate the FSA specification
- `generate_structure` - Generate the basic class structure
- `add_logic` - Add FSA logic and methods
- `complete` - Finalize and return generated code

## Usage

```python
from agno.fsa import FSAGenerator

# Create generator instance
generator = FSAGenerator()

# Define FSA specification
fsa_name = "TrafficLight"
states = ["red", "yellow", "green"]
transitions = {
    ("red", "timer"): "green",
    ("green", "timer"): "yellow",
    ("yellow", "timer"): "red",
}
purpose = "A simple traffic light FSA that cycles through states."

# Generate FSA code
code = generator.generate(fsa_name, states, transitions, purpose)

# Save to file
generator.save_to_file("traffic_light_fsa.py")
```

## Generated FSA Features

Each generated FSA includes:

- **State Management**: Automatic initialization with first state
- **Transition Logic**: State transitions based on input symbols
- **History Tracking**: Complete history of state transitions
- **Validation**: Check if transitions are valid
- **Available Transitions**: Query available inputs from current state
- **Run Method**: Process sequences of inputs and return results

## Generated FSA Methods

- `transition(input_symbol)` - Perform a state transition
- `reset()` - Reset to initial state
- `get_state()` - Get current state
- `get_history()` - Get transition history
- `is_valid_transition(input_symbol)` - Check if transition is valid
- `get_available_transitions()` - Get available inputs from current state
- `run(inputs)` - Run FSA with sequence of inputs

## Example Output

```python
class TrafficLight:
    """A simple traffic light FSA."""

    def __init__(self):
        self.state = "red"
        self.states = ['red', 'yellow', 'green']
        self.transitions = {
            ("red", "timer"): "green",
            ("green", "timer"): "yellow",
            ("yellow", "timer"): "red",
        }
        self.history = []

    # ... (all methods included)
```

## Input Specification

### fsa_name
- Type: `str`
- Must be a valid Python identifier
- Used as the class name

### states_list
- Type: `List[str]`
- List of state names
- All must be valid Python identifiers
- First state is used as initial state

### transitions_dict
- Type: `Dict[tuple, str]`
- Keys: `(current_state, input_symbol)` tuples
- Values: `next_state` strings
- All states must exist in `states_list`

### purpose_description
- Type: `str`
- Description of the FSA's purpose
- Used in generated docstring

## Validation

The generator validates:
- FSA name is a valid Python identifier
- States list is non-empty with valid identifiers
- All transition states exist in states list
- Transitions dictionary is properly formatted

Invalid specifications raise `ValueError` with detailed error messages.

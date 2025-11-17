# FSA (Finite State Automaton) Module

The FSA module provides a framework for creating state-based agents and workflows in agno.

## Overview

FSAs (Finite State Automatons) are computational models that manage state transitions and execution flow with explicit states, transitions, and validation rules. They provide a structured approach to building agents and workflows that require clear state management.

## Key Components

### Base FSA Class

The `FSA` base class provides:
- State management with validation
- Transition definitions with conditions and actions
- State history tracking
- Session state persistence
- Support for stateful and stateless patterns
- Cascade-aware capabilities

### FSA Generator

The `FSAGeneratorFSA` is a meta-FSA that generates new FSA implementations from specifications:
- Template-based code generation
- AST-based validation
- Automatic test generation
- MLA v3.0 standards compliance
- Support for multiple FSA patterns

## Usage

### Creating a Simple FSA

```python
from agno.fsa import FSA
from dataclasses import dataclass

@dataclass
class MyFSA(FSA):
    """Custom FSA implementation."""

    def __post_init__(self):
        self.states = {"initial", "processing", "completed", "error"}
        self.add_transition("initial", "processing")
        self.add_transition("processing", "completed")
        super().__post_init__()

    def run(self, **kwargs):
        """Execute the FSA."""
        self.transition("processing")
        # ... do work ...
        self.transition("completed")
        return {"status": "success"}

# Use the FSA
fsa = MyFSA()
result = fsa.run()
```

### Generating an FSA

```python
from agno.fsa import FSAGeneratorFSA, FSASpecification

# Define specification
spec = FSASpecification(
    name="DataProcessorFSA",
    purpose="Process data through multiple stages",
    states={"initial", "loading", "processing", "completed", "error"},
    methods=[
        {
            "name": "load_data",
            "params": [{"name": "source", "type": "str"}],
            "return_type": "Dict",
            "docstring": "Load data from source"
        }
    ],
    stateful=True
)

# Generate FSA
generator = FSAGeneratorFSA()
result = generator.run(spec)

if result["success"]:
    print(f"Generated: {result['fsa_name']}")
    print(f"Files: {result['generated_files']}")
```

## FSA Patterns

### Stateful FSA

Maintains state across invocations:

```python
spec = FSASpecification(
    name="StatefulFSA",
    purpose="Maintains state across runs",
    stateful=True
)
```

### Stateless FSA

Resets state after each invocation:

```python
spec = FSASpecification(
    name="StatelessFSA",
    purpose="One-time execution",
    stateful=False
)
```

### Cascade-Aware FSA

Can cascade execution to other FSAs:

```python
spec = FSASpecification(
    name="OrchestratorFSA",
    purpose="Orchestrates multiple FSAs",
    cascade_aware=True
)
```

## Validation

FSA specifications are validated against MLA v3.0 standards:
- Names must end with "FSA" and use PascalCase
- Must include "initial" state
- Method names must use snake_case
- All transitions must reference valid states

## Examples

See `cookbook/agent_concepts/fsa/` for comprehensive examples:
- Basic FSA generation
- Custom methods
- Cascade-aware FSAs
- Validation examples
- State inspection

## Testing

The FSA module includes comprehensive tests:

```bash
pytest libs/agno/tests/unit/fsa/
```

Generated FSAs automatically include test suites.

## Architecture

```
libs/agno/agno/fsa/
├── __init__.py          # Module exports
├── base.py              # Base FSA class
├── generator.py         # FSA Generator
└── generated/           # Generated FSAs

libs/agno/tests/unit/fsa/
├── test_base.py         # Base FSA tests
├── test_generator.py    # Generator tests
└── generated/           # Generated FSA tests
```

## Best Practices

1. **Define clear states**: Use descriptive state names that reflect the FSA's purpose
2. **Validate transitions**: Add conditions to transitions for complex logic
3. **Track history**: Use state_history and transition_history for debugging
4. **Test thoroughly**: Generated tests provide a good starting point
5. **Use session_state**: Store data that needs to persist across states

## Future Enhancements

- Visual FSA diagram generation
- FSA composition and chaining
- Advanced cascade patterns
- State persistence to database
- Real-time FSA monitoring

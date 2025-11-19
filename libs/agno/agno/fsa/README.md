# FSA (Finite State Automaton) Module

This module provides a flexible FSA framework for implementing state-based workflows in Agno.

## Components

### Base FSA Framework (`base.py`)

- **`FSA`**: Base class for creating finite state automata
- **`State`**: Enum for defining states
- **`Transition`**: Class for defining state transitions with conditions and actions

### Quality Metrics Calculator (`quality_metrics.py`)

A specialized FSA for calculating comprehensive code quality metrics.

## Quality Metrics Calculator

### Features

- **Cyclomatic Complexity Analysis**: Measures code complexity
- **Test Coverage Analysis**: Evaluates test coverage
- **Code Duplication Detection**: Identifies duplicate code blocks
- **Maintainability Index**: Calculates maintainability score
- **Technical Debt Ratio**: Estimates technical debt
- **Automated Recommendations**: Generates actionable improvement suggestions

### States

The Quality Metrics Calculator FSA transitions through these states:

1. `INITIAL` - Starting state
2. `LOADING_FILES` - Loading code files
3. `ANALYZING_COMPLEXITY` - Calculating cyclomatic complexity
4. `ANALYZING_COVERAGE` - Analyzing test coverage
5. `ANALYZING_DUPLICATION` - Detecting code duplication
6. `COMPUTING_SCORES` - Computing composite quality scores
7. `GENERATING_RECOMMENDATIONS` - Generating recommendations
8. `COMPLETED` - Final state

### Usage

```python
from agno.fsa import QualityMetricsCalculator

# Create calculator
calculator = QualityMetricsCalculator()

# Analyze code files
results = calculator.calculate(
    code_files=["path/to/file1.py", "path/to/file2.py"],
    test_results={
        "total_tests": 25,
        "passed_tests": 22,
        "coverage_percentage": 75.5,
    },
)

# Access results
print(f"Overall Score: {results['quality_scores'].overall_score}/100")
print(f"Maintainability Index: {results['maintainability_index']}/100")
print(f"Technical Debt Ratio: {results['debt_ratio']}")

# View recommendations
for rec in results["recommendations"]:
    print(f"{rec['category']}: {rec['message']}")
```

### Outputs

The calculator returns a dictionary with:

- **`quality_scores`**: `QualityScores` object containing:
  - `overall_score`: Overall quality score (0-100)
  - `maintainability_index`: Maintainability index (0-100)
  - `complexity_score`: Complexity score (0-100)
  - `code_coverage`: Test coverage percentage
  - `duplication_score`: Duplication score (0-100)
  - `technical_debt_ratio`: Technical debt ratio (0-1)

- **`metrics`**: Per-file metrics including:
  - Lines of code
  - Cyclomatic complexity
  - Function and class counts
  - Average function complexity

- **`duplication_data`**: Duplication analysis:
  - Total lines
  - Duplicated lines
  - Duplication percentage
  - Duplicate code blocks

- **`recommendations`**: List of actionable recommendations with:
  - Category
  - Severity (high/medium/info)
  - Message
  - Details

## Examples

See `/home/user/agno/cookbook/fsa/quality_metrics_example.py` for comprehensive examples.

## Creating Custom FSAs

```python
from agno.fsa.base import FSA, State, Transition
from enum import Enum

class MyState(str, Enum):
    INITIAL = "initial"
    PROCESSING = "processing"
    COMPLETED = "completed"

class MyFSA(FSA):
    def __init__(self):
        super().__init__(name="MyFSA", initial_state=MyState.INITIAL)
        self._setup_transitions()

    def _setup_transitions(self):
        transitions = [
            Transition(
                from_state=MyState.INITIAL,
                to_state=MyState.PROCESSING,
                condition=lambda ctx: "data" in ctx,
                action=self._process_data,
            ),
            Transition(
                from_state=MyState.PROCESSING,
                to_state=MyState.COMPLETED,
                action=lambda ctx: ctx,
            ),
        ]
        self.register_transitions(transitions)

    def _process_data(self, context):
        # Custom processing logic
        context["result"] = process(context["data"])
        return context

# Use the FSA
fsa = MyFSA()
result = fsa.run({"data": "input"})
```

## License

Part of the Agno framework.

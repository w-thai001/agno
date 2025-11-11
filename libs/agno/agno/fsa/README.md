# FSA: Fractal Self-Assembly Code Optimization

The FSA (Fractal Self-Assembly) module provides a recursive self-improvement framework for automated code optimization. It combines quality assessment, multi-step improvements, and convergence detection to iteratively enhance code quality.

## Components

### FSA-2.1: Quality Assessment (`QualityAssessor`)

Comprehensive code quality assessment across multiple dimensions:

- **Readability**: Code formatting, spacing, and visual clarity
- **Maintainability**: Ease of modification and extension
- **Efficiency**: Algorithm complexity and performance
- **Documentation**: Comments, docstrings, and explanations
- **Naming Quality**: Variable and function name descriptiveness
- **Structure**: Code organization and indentation
- **Best Practices**: Language-specific conventions

**Output**: Detailed quality metrics with scores (0-100) for each dimension, plus strengths, weaknesses, and actionable suggestions.

### FSA-3.1: Multi-Step Improvements (`CodeImprover`)

Applies targeted improvements based on quality assessment:

1. **Naming Improvements**: Expands abbreviations, creates descriptive names
2. **Documentation**: Adds JSDoc, docstrings, and inline comments
3. **Structure**: Fixes formatting, indentation, and spacing
4. **Readability**: Improves visual clarity and organization
5. **Best Practices**: Applies language-specific conventions
6. **Efficiency**: Optimizes algorithms and data structures

**Features**:
- Incremental improvements (one area at a time)
- Language-aware transformations
- Priority-based improvement planning

### FSA-3.2: RSI Code Optimizer (`RSICodeOptimizer`)

Orchestrates the recursive self-improvement loop:

```
Assess → Improve → Validate → Repeat
```

**RSI Loop**:
1. **Assess**: Evaluate current code quality (FSA-2.1)
2. **Identify**: Determine focus areas needing improvement
3. **Improve**: Apply targeted enhancements (FSA-3.1)
4. **Validate**: Measure quality improvement
5. **Converge**: Check convergence conditions
6. **Repeat**: Continue until convergence

**Convergence Detection**:
- **Quality Plateau**: Improvement below threshold for N iterations
- **Target Achievement**: Quality score reaches target (e.g., 90/100)
- **Maximum Iterations**: Safety limit reached

**Performance Metrics**:
- Quality score per iteration
- Improvement delta per iteration
- Cumulative improvement
- Average improvement rate
- Convergence status and reason

## Installation

The FSA module is part of the Agno library:

```python
from agno.fsa import QualityAssessor, CodeImprover, RSICodeOptimizer
```

## Usage

### Basic Usage

```python
from agno.fsa import RSICodeOptimizer

# Initialize optimizer
optimizer = RSICodeOptimizer(
    convergence_threshold=2.0,  # Stop if improvement < 2 points
    plateau_patience=2,          # Wait 2 iterations for plateau
    max_iterations=5,            # Maximum iterations
    target_quality=90.0,         # Target quality score
)

# Your code to optimize
code = """function calc(a,b){return a+b}"""

# Execute RSI loop
result = optimizer.improve_code(
    code=code,
    iterations=5,
    language="javascript",
    verbose=True,
)

# Access results
print(f"Initial Quality: {result.initial_quality:.2f}/100")
print(f"Final Quality: {result.final_quality:.2f}/100")
print(f"Total Improvement: +{result.total_improvement:.2f} points")
print(f"Converged: {result.converged}")
```

### Quality Assessment Only

```python
from agno.fsa import QualityAssessor

assessor = QualityAssessor()
metrics = assessor.assess(code)

print(f"Overall Score: {metrics.overall_score:.2f}/100")
print(f"Readability: {metrics.readability:.2f}/100")
print(f"Documentation: {metrics.documentation:.2f}/100")
print(f"Strengths: {metrics.strengths}")
print(f"Weaknesses: {metrics.weaknesses}")
print(f"Suggestions: {metrics.suggestions}")
```

### Code Improvement Only

```python
from agno.fsa import CodeImprover

improver = CodeImprover()

# Improve all areas
improved = improver.improve(code)

# Improve specific areas
improved = improver.improve(
    code,
    focus_areas=["naming", "documentation"],
    language="javascript"
)

# Incremental improvement
improved = improver.apply_incremental_improvement(
    code,
    focus_area="naming",
    language="javascript"
)
```

### Tracking Progress

```python
# Get progress metrics
progress = optimizer.track_progress(result)

print(f"Total Iterations: {progress['total_iterations']}")
print(f"Improvement %: {progress['improvement_percentage']:.1f}%")
print(f"Avg Rate: {progress['avg_improvement_rate']:.2f} pts/iter")

# Get quality trajectory
trajectory = result.get_quality_trajectory()
for iteration, score in trajectory:
    print(f"Iteration {iteration}: {score:.2f}/100")
```

### Export Results

```python
# Export to JSON
optimizer.export_results(result, "optimization_results.json")

# Print summary report
result.print_summary()
```

## Demo Scripts

### Quick Demo

```bash
cd libs/agno
python -m agno.fsa.demo_rsi
```

Demonstrates RSI optimization with convergence on target quality.

### Full 5-Iteration Demo

```bash
cd libs/agno
python -m agno.fsa.demo_full_rsi
```

Demonstrates complete 5-iteration loop with detailed metrics.

## Example Output

```
======================================================================
RSI CODE OPTIMIZATION SUMMARY
======================================================================

Initial Quality Score: 86.50/100
Final Quality Score:   94.30/100
Total Improvement:     +7.80 points
Iterations:            5
Avg Improvement Rate:  1.56 points/iteration
Converged:             True
Reason:                Quality plateau reached

----------------------------------------------------------------------
QUALITY TRAJECTORY (iteration -> score)
----------------------------------------------------------------------
Iteration 1: 86.50 ███████████████████████████████████████████
Iteration 2: 93.79 ██████████████████████████████████████████████
Iteration 3: 94.12 ███████████████████████████████████████████████
Iteration 4: 94.24 ███████████████████████████████████████████████
Iteration 5: 94.30 ███████████████████████████████████████████████
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           FSA-3.2: RSI Code Optimizer           │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │   RSI LOOP (Recursive Self-Improvement)   │ │
│  │                                           │ │
│  │   1. Assess Quality (FSA-2.1)           │ │
│  │   2. Identify Focus Areas                │ │
│  │   3. Apply Improvements (FSA-3.1)       │ │
│  │   4. Validate Changes                    │ │
│  │   5. Check Convergence                   │ │
│  │   6. Repeat or Stop                      │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌──────────────┐      ┌───────────────┐      │
│  │   FSA-2.1    │      │   FSA-3.1     │      │
│  │   Quality    │─────▶│     Code      │      │
│  │  Assessor    │      │   Improver    │      │
│  └──────────────┘      └───────────────┘      │
└─────────────────────────────────────────────────┘
```

## Configuration

### Optimizer Parameters

- **convergence_threshold** (float): Minimum improvement to continue (default: 2.0)
- **plateau_patience** (int): Iterations to wait before declaring plateau (default: 2)
- **max_iterations** (int): Maximum optimization iterations (default: 10)
- **target_quality** (float): Target quality score 0-100 (default: 90.0)

### Quality Weights

Customize dimension weights in `QualityAssessor`:

```python
assessor = QualityAssessor()
assessor.weights = {
    "readability": 0.25,      # Increased from 0.20
    "maintainability": 0.15,
    "efficiency": 0.10,       # Decreased from 0.15
    "documentation": 0.15,    # Increased from 0.10
    "naming_quality": 0.15,
    "structure": 0.15,
    "best_practices": 0.05,   # Decreased from 0.10
}
```

## Supported Languages

Currently supports:
- JavaScript
- Python
- Java
- C++
- Generic (fallback)

Language detection is automatic based on syntax patterns.

## Performance Characteristics

- **Time Complexity**: O(n × m) where n = iterations, m = code length
- **Space Complexity**: O(n × m) for storing iteration history
- **Typical Runtime**: < 1 second for small code snippets
- **Convergence**: Usually 2-5 iterations for most code

## Limitations

1. **Static Analysis Only**: No runtime execution or testing
2. **Heuristic-Based**: Quality metrics use pattern matching
3. **Limited Context**: Cannot understand business logic
4. **Surface-Level**: Focuses on style and structure, not algorithms
5. **Additive Docs**: May duplicate documentation if applied multiple times

## Future Enhancements

- [ ] Integration with AST parsing for deeper analysis
- [ ] LLM-powered semantic understanding
- [ ] Language-specific linters integration
- [ ] Automated test generation
- [ ] Performance profiling integration
- [ ] Security vulnerability detection
- [ ] Code complexity metrics (cyclomatic, cognitive)
- [ ] Refactoring pattern suggestions

## Contributing

To extend the FSA module:

1. Add new quality metrics in `quality_assessor.py`
2. Implement new improvement strategies in `code_improver.py`
3. Update convergence logic in `rsi_optimizer.py`
4. Add language-specific rules
5. Write tests and documentation

## License

Part of the Agno library. See main LICENSE file.

## References

- **Recursive Self-Improvement**: Inspired by AI safety research on RSI systems
- **Code Quality Metrics**: Based on software engineering best practices
- **Convergence Detection**: Adapted from optimization algorithms in ML

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/agno-agi/agno
- Documentation: https://docs.agno.com
- Community: https://community.agno.com

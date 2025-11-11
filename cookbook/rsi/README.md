# FSA-3.2: RSI Code Optimizer

Recursive Self-Improvement (RSI) system that iteratively optimizes code through multiple improvement cycles with automatic quality assessment, convergence detection, and comprehensive metrics tracking.

## Overview

The RSI Code Optimizer implements a recursive self-improvement loop that:
1. Assesses code quality using FSA-2.1
2. Generates improvements (rule-based for demo, LLM-ready for production)
3. Applies improvements iteratively
4. Tracks quality improvements across iterations
5. Detects convergence (plateau, target reached, or max iterations)
6. Provides rollback if quality degrades
7. Reports comprehensive metrics

## Features

### Recursive Self-Improvement Loop
- Iterative optimization with configurable max iterations
- Quality assessment at each iteration
- Improvement generation and application
- Automatic convergence detection

### Quality Tracking
- Per-iteration quality scores
- Quality delta measurement
- Dimension-level tracking (syntax, security, style, performance, best practices)
- Improvement trajectory visualization

### Convergence Detection
- **Quality Threshold**: Stop when target quality reached
- **Improvement Plateau**: Stop when improvement < threshold
- **Perfect Score**: Stop at 100/100
- **Max Iterations**: Stop after max iterations
- **Quality Degradation**: Rollback if quality decreases

### Comprehensive Metrics
- Iteration-by-iteration tracking
- Quality improvement trajectory
- Dimension scores evolution
- Applied improvements list
- Execution time per iteration
- Total optimization time

## Installation

```bash
pip install agno
```

## Quick Start

```python
from agno.rsi import RSICodeOptimizer

# Initialize optimizer
optimizer = RSICodeOptimizer(
    convergence_threshold=2.0,  # Min improvement per iteration
    quality_target=95.0,         # Target quality score
    max_iterations=5             # Max iterations
)

# Code with issues
code = '''
def get_user(user_id):
    query = "SELECT * FROM users WHERE id='" + str(user_id) + "'"
    return eval(query)
'''

# Run RSI optimization
result = optimizer.optimizeCode(
    code,
    language="python",
    max_iterations=5
)

print(f"Quality: {result.original_quality:.1f} → {result.final_quality:.1f}")
print(f"Improvement: {result.total_improvement:+.1f} points")
print(f"Iterations: {len(result.iterations)}")
```

## Core Methods

### `optimizeCode(code, language, max_iterations)`

Main RSI optimization loop.

**Parameters:**
- `code` (str): Source code to optimize
- `language` (str): Programming language (python, javascript)
- `max_iterations` (int, optional): Override default max iterations

**Returns:** `OptimizationResult` with complete optimization history

```python
result = optimizer.optimizeCode(code, "python", max_iterations=5)

# Access results
print(result.original_quality)    # Initial quality score
print(result.final_quality)       # Final quality score
print(result.total_improvement)   # Total improvement
print(result.optimized_code)      # Improved code
print(result.convergence_reason)  # Why loop stopped
print(result.iterations)          # List of IterationMetrics
```

### `assessQuality(code, language)`

Assess code quality using FSA-2.1.

**Parameters:**
- `code` (str): Source code
- `language` (str): Programming language

**Returns:** Quality score (0-100)

```python
quality = optimizer.assessQuality(code, "python")
print(f"Quality: {quality}/100")
```

### `generateImprovements(code, language, iteration)`

Generate improvements for code.

**Parameters:**
- `code` (str): Source code
- `language` (str): Programming language
- `iteration` (int): Current iteration number

**Returns:** Tuple of (improved_code, improvements_list)

```python
improved_code, improvements = optimizer.generateImprovements(
    code, "python", iteration=1
)

for improvement in improvements:
    print(f"  • {improvement}")
```

### `trackIteration(iteration, quality_score, quality_delta, code, improvements, language)`

Track metrics for an iteration.

**Parameters:**
- `iteration` (int): Iteration number
- `quality_score` (float): Quality score achieved
- `quality_delta` (float): Improvement from previous
- `code` (str): Current code state
- `improvements` (List[str]): Improvements applied
- `language` (str): Programming language

```python
optimizer.trackIteration(
    iteration=1,
    quality_score=95.0,
    quality_delta=+5.0,
    code=improved_code,
    improvements=["Fixed eval() usage", "Added docstrings"],
    language="python"
)
```

## Optimization Result

The `OptimizationResult` object contains:

```python
result = optimizer.optimizeCode(...)

# Quality metrics
result.original_quality     # Initial quality score
result.final_quality        # Final quality score
result.total_improvement    # Total improvement (+/- points)

# Code
result.original_code        # Original code
result.optimized_code       # Improved code

# Iteration data
result.iterations           # List[IterationMetrics]
result.convergence_reason   # ConvergenceReason enum

# Metadata
result.total_time_ms       # Total optimization time
result.success             # True if improved
result.language            # Programming language
result.summary             # Human-readable summary
```

## Iteration Metrics

Each iteration records comprehensive metrics:

```python
metrics = result.iterations[0]

metrics.iteration             # Iteration number
metrics.quality_score         # Quality score
metrics.quality_delta         # Change from previous
metrics.dimension_scores      # Dict of dimension scores
metrics.improvements_applied  # List of improvements
metrics.code_length          # Code length in characters
metrics.validation_time_ms   # Validation time
metrics.issues_fixed         # Number of issues fixed
metrics.timestamp            # Timestamp
```

## Convergence Reasons

The optimizer stops when:

| Reason | Description | Example |
|--------|-------------|---------|
| `QUALITY_THRESHOLD` | Target quality reached | Quality ≥ 95.0 |
| `IMPROVEMENT_PLATEAU` | Improvement < threshold | Delta < 2.0 |
| `PERFECT_SCORE` | Perfect quality achieved | Quality = 100.0 |
| `MAX_ITERATIONS` | Max iterations reached | Iteration = 10 |
| `QUALITY_DEGRADATION` | Quality decreased | Delta < -1.0 |

## Configuration

### Quality Target

```python
# Lenient target (85/100)
optimizer = RSICodeOptimizer(quality_target=85.0)

# Standard target (95/100)
optimizer = RSICodeOptimizer(quality_target=95.0)

# Strict target (98/100)
optimizer = RSICodeOptimizer(quality_target=98.0)
```

### Convergence Threshold

```python
# Loose threshold (continue with 1+ improvement)
optimizer = RSICodeOptimizer(convergence_threshold=1.0)

# Standard threshold (continue with 2+ improvement)
optimizer = RSICodeOptimizer(convergence_threshold=2.0)

# Strict threshold (continue with 5+ improvement)
optimizer = RSICodeOptimizer(convergence_threshold=5.0)
```

### Max Iterations

```python
# Quick optimization (3 iterations)
optimizer = RSICodeOptimizer(max_iterations=3)

# Standard optimization (5 iterations)
optimizer = RSICodeOptimizer(max_iterations=5)

# Deep optimization (10 iterations)
optimizer = RSICodeOptimizer(max_iterations=10)
```

## Improvement Types

The optimizer applies various improvement types:

| Type | Description | Example |
|------|-------------|---------|
| `SECURITY_FIX` | Fix security vulnerabilities | Replace eval() with ast.literal_eval() |
| `STYLE_IMPROVEMENT` | Improve code style | Add docstrings, fix naming |
| `PERFORMANCE_OPTIMIZATION` | Optimize performance | Improve loop patterns |
| `ERROR_HANDLING` | Add error handling | Add try/except blocks |
| `DOCUMENTATION` | Improve documentation | Add docstrings, comments |
| `BEST_PRACTICES` | Apply best practices | Follow conventions |

## Examples

### Example 1: Security Improvements

```python
optimizer = RSICodeOptimizer(max_iterations=5)

code = '''
def get_data(input):
    result = eval(input)
    return result
'''

result = optimizer.optimizeCode(code, "python")

# Result:
# Quality: 82.0 → 95.0 (+13.0)
# Improvements:
#   - Replaced eval() with ast.literal_eval()
#   - Added docstrings
#   - Fixed naming conventions
```

### Example 2: Convergence Detection

```python
optimizer = RSICodeOptimizer(
    convergence_threshold=1.0,
    quality_target=98.0
)

code = '''
def calculate_average(numbers):
    """Calculate average."""
    return sum(numbers) / len(numbers)
'''

result = optimizer.optimizeCode(code, "python")

# Result:
# Quality: 95.0 → 95.0 (+0.0)
# Convergence: improvement_plateau
# Iterations: 0 (already good quality)
```

### Example 3: Multi-Iteration Optimization

```python
optimizer = RSICodeOptimizer(max_iterations=7)

code = '''
password = "admin123"

def processData(input):
    result = eval(input)
    return result
'''

result = optimizer.optimizeCode(code, "python", max_iterations=7)

# Iteration 1: Security fixes (eval, hardcoded secrets)
# Iteration 2: Style improvements (naming, docstrings)
# Iteration 3: Error handling added
# Iteration 4: Further refinements
# ...
# Convergence: quality_threshold
```

### Example 4: Metrics Tracking

```python
optimizer = RSICodeOptimizer(max_iterations=5)
result = optimizer.optimizeCode(code, "python")

# Get quality trajectory
for i, metrics in enumerate(result.iterations):
    print(f"Iteration {i+1}:")
    print(f"  Quality: {metrics.quality_score:.1f} ({metrics.quality_delta:+.1f})")
    print(f"  Improvements: {len(metrics.improvements_applied)}")

# Get dimension trajectories
trajectories = optimizer.get_dimension_trajectories()
for dim, scores in trajectories.items():
    print(f"{dim}: {scores}")
```

## Visualization

### Quality Trajectory

```python
result = optimizer.optimizeCode(code, "python")

# ASCII visualization
qualities = [result.original_quality] + [m.quality_score for m in result.iterations]

for i, quality in enumerate(qualities):
    bar = "█" * int(quality / 100 * 60)
    label = "Initial" if i == 0 else f"Iter {i}"
    print(f"{label:<8} {quality:5.1f} | {bar}")
```

### Dimension Evolution

```python
# Show how each dimension improved
for metrics in result.iterations:
    print(f"\nIteration {metrics.iteration}:")
    for dim, score in metrics.dimension_scores.items():
        print(f"  {dim}: {score}/100")
```

## Integration with FSA Components

### FSA-2.1: Code Quality Validator

The RSI optimizer uses FSA-2.1 for quality assessment:

```python
# Automatic integration
optimizer = RSICodeOptimizer()

# Or provide custom validator
from agno.validator import CodeQualityValidator

validator = CodeQualityValidator(min_quality_score=80)
optimizer = RSICodeOptimizer(validator=validator)
```

### FSA-3.1: Multi-Step Code Builder (Production)

For production use with LLM-powered improvements:

```python
from agno.builder import MultiStepCodeBuilder

# Custom improvement generation
class LLMRSIOptimizer(RSICodeOptimizer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.builder = MultiStepCodeBuilder()

    def generateImprovements(self, code, language, iteration):
        # Use FSA-3.1 + LLM for intelligent improvements
        # (Implementation would use LLM API)
        pass
```

## Running the Demo

```bash
python cookbook/rsi/rsi_demo.py
```

**7 Comprehensive Demos:**
1. **Basic RSI Optimization** - Simple optimization loop
2. **Convergence Detection** - Automatic stopping
3. **Multiple Improvement Types** - Security, style, etc.
4. **Dimension Tracking** - Per-dimension evolution
5. **Trajectory Visualization** - Quality improvement graph
6. **Metrics Dashboard** - Comprehensive metrics
7. **Before/After Comparison** - Side-by-side comparison

## Sample Output

```
================================================================================
  Demo 1: Basic RSI Optimization
================================================================================

Original Code:
def get_user(user_id):
    query = "SELECT * FROM users WHERE id='" + str(user_id) + "'"
    return eval(query)

RSI Optimization SUCCESS
Quality: 82.0 → 95.0 (+13.0)
Iterations: 2
Convergence: quality_threshold

Iter   Quality    Delta      Improvements
--------------------------------------------------------------------------------
0      82.00      -          (Initial)
1      90.00      +8.00      Replaced eval(), Added docstrings
2      95.00      +5.00      Fixed SQL injection, Added error handling

Quality Improvement Trajectory:
--------------------------------------------------------------------------------
Initial   82.0 | ████████████████████████████████████████████░░
Iter 1    90.0 | ████████████████████████████████████████████████
Iter 2    95.0 | ████████████████████████████████████████████████████
--------------------------------------------------------------------------------
Improvement: +13.0 points

Optimized Code:
import ast

def get_user(user_id):
    """Get user by ID."""
    try:
        query = "SELECT * FROM users WHERE id=?"
        result = conn.execute(query, (user_id,))
        return result.fetchone()
    except Exception as e:
        raise
```

## Metrics Dashboard

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                      RSI OPTIMIZATION METRICS DASHBOARD                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 Overall Statistics
├─ Initial Quality:      82.00/100
├─ Final Quality:        95.00/100
├─ Total Improvement:    +13.00 points
├─ Iterations:           2
├─ Convergence:          quality_threshold
├─ Success:              YES ✓
└─ Total Time:           15ms

🔄 Iteration Summary
├─ Iteration 1
│  ├─ Quality:          90.00/100 (+8.00)
│  ├─ Improvements:     2
│  └─ Validation Time:  2.5ms
├─ Iteration 2
│  ├─ Quality:          95.00/100 (+5.00)
│  ├─ Improvements:     2
│  └─ Validation Time:  2.3ms

🎯 Dimension Breakdown (Final)
├─ syntax               [████████████████████████████████████████] 100/100
├─ style                [████████████████████████████████████░░░░] 90/100
├─ security             [████████████████████████████████████████] 100/100
├─ performance          [████████████████████████████████████████] 100/100
├─ best_practices       [██████████████████████████████████░░░░░░] 85/100

✨ Improvements Applied
├─ Replaced eval() with safer ast.literal_eval()
├─ Added docstrings to functions
├─ Fixed SQL injection vulnerability
└─ Added comprehensive error handling
```

## Best Practices

1. **Set Appropriate Targets** - Use realistic quality targets (85-95)
2. **Monitor Convergence** - Check convergence reasons
3. **Review Improvements** - Verify applied improvements
4. **Track Metrics** - Monitor iteration metrics
5. **Test Iteratively** - Start with lower max_iterations
6. **Validate Results** - Always review optimized code

## Limitations

- Rule-based improvements (production would use LLM)
- Limited to predefined improvement types
- Requires FSA-2.1 for quality assessment
- Python and JavaScript support only

## Future Enhancements

- LLM-powered improvement generation
- Custom improvement rules
- Multi-language support
- Parallel improvement exploration
- A/B testing of improvements
- Machine learning-based convergence prediction

## Architecture

```
RSICodeOptimizer
├── optimizeCode() [Main Loop]
│   ├── assessQuality() → FSA-2.1
│   ├── For each iteration:
│   │   ├── generateImprovements()
│   │   ├── Apply improvements
│   │   ├── Re-assess quality
│   │   ├── Check convergence
│   │   └── trackIteration()
│   └── Return OptimizationResult
├── assessQuality() → FSA-2.1
├── generateImprovements() → [Rule-based / FSA-3.1 + LLM]
└── trackIteration() → IterationMetrics
```

## License

Same as the parent Agno project.

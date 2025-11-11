# FSA-4.1: Meta-FSA Orchestrator

The Meta-FSA Orchestrator is the capstone component of the FSA ecosystem, providing intelligent coordination of all FSA components with automated task decomposition, optimal FSA sequencing, and meta-learning capabilities.

## Overview

The Meta-FSA Orchestrator coordinates:
- **FSA-1.1**: Prompt Optimizer
- **FSA-1.2**: Code Template Library
- **FSA-2.1**: Code Quality Validator
- **FSA-2.2**: Multi-Model Orchestrator
- **FSA-3.1**: Multi-Step Code Builder
- **FSA-3.2**: RSI Code Optimizer

## Features

### Intelligent Task Decomposition
- Analyzes high-level tasks
- Breaks down into FSA-appropriate components
- Identifies dependencies between components
- Assigns priorities and complexity estimates

### Optimal FSA Sequencing
- Dependency-aware execution ordering
- Topological sort for FSA chain
- Performance-based FSA selection
- Automatic data flow between FSAs

### Performance Tracking
- Per-FSA execution metrics
- Success rate monitoring
- Average execution time tracking
- Total time and execution count

### Meta-Learning
- Learns successful FSA chains
- Identifies performance bottlenecks
- Tracks complexity vs execution time patterns
- Builds pattern library for future optimizations

### Unified API
- Single entry point for all FSA operations
- Consistent error handling
- Comprehensive result objects
- Detailed execution metrics

## Installation

```bash
pip install agno
```

## Quick Start

```python
from agno.meta import MetaFSAOrchestrator, TaskType

# Initialize orchestrator
orchestrator = MetaFSAOrchestrator()

# Orchestrate complete project build
result = orchestrator.orchestrate(
    task="Build a REST API for user authentication with JWT tokens",
    task_type=TaskType.PROJECT_BUILD,
    language="python",
    config={
        "budget": {"max_cost_usd": 1.0},
        "quality_target": 95.0,
        "rsi_iterations": 3
    }
)

print(f"Success: {result.success}")
print(f"FSA Chain: {' → '.join([fsa.value for fsa in result.execution_sequence])}")
print(f"Total Time: {result.total_time_ms:.0f}ms")
```

## Core Methods

### `orchestrate(task, task_type, language, config)`

Main orchestration method coordinating all FSAs.

**Parameters:**
- `task` (str): High-level task description
- `task_type` (TaskType): Type of task (PROJECT_BUILD, CODE_OPTIMIZATION, etc.)
- `language` (str): Programming language (default: "python")
- `config` (Dict, optional): Configuration including budget, quality targets, etc.

**Returns:** `OrchestrationResult` with complete execution details

```python
result = orchestrator.orchestrate(
    task="Build user authentication API",
    task_type=TaskType.PROJECT_BUILD,
    language="python",
    config={
        "budget": {"max_cost_usd": 1.0, "max_latency_ms": 5000},
        "quality_target": 95.0,
        "rsi_iterations": 3
    }
)
```

### `decompose(task, task_type, language, config)`

Decompose high-level task into FSA-appropriate components.

**Parameters:**
- `task` (str): Task description
- `task_type` (TaskType): Type of task
- `language` (str): Programming language
- `config` (Dict): Configuration

**Returns:** List of `TaskComponent` objects

```python
components = orchestrator.decompose(
    task="Build authentication API",
    task_type=TaskType.PROJECT_BUILD,
    language="python",
    config={}
)

for component in components:
    print(f"• {component.description}")
    print(f"  FSAs: {[fsa.value for fsa in component.required_fsas]}")
```

### `selectFSAs(task_components)`

Select optimal FSA execution sequence based on dependencies.

**Parameters:**
- `task_components` (List[TaskComponent]): Decomposed task components

**Returns:** Ordered list of FSA types to execute

```python
fsa_sequence = orchestrator.selectFSAs(components)
print(f"FSA Chain: {' → '.join([fsa.value for fsa in fsa_sequence])}")
```

### `executeSequence(fsa_sequence, task_components, language, config)`

Execute FSA sequence with proper data flow.

**Parameters:**
- `fsa_sequence` (List[FSAType]): Ordered FSA types
- `task_components` (List[TaskComponent]): Task components
- `language` (str): Programming language
- `config` (Dict): Configuration

**Returns:** List of `FSAExecutionResult` objects

```python
results = orchestrator.executeSequence(
    fsa_sequence=fsa_sequence,
    task_components=components,
    language="python",
    config={}
)

for result in results:
    print(f"{result.fsa_type.value}: {result.execution_time_ms:.1f}ms")
```

### `trackPerformance(fsa_type, execution_time_ms, success)`

Track FSA performance metrics.

**Parameters:**
- `fsa_type` (FSAType): FSA type
- `execution_time_ms` (float): Execution time
- `success` (bool): Whether execution succeeded

```python
orchestrator.trackPerformance(
    fsa_type=FSAType.QUALITY_VALIDATOR,
    execution_time_ms=45.2,
    success=True
)
```

### `learnFromExecution(task_components, execution_sequence, results)`

Learn patterns from execution for future optimizations.

**Parameters:**
- `task_components` (List[TaskComponent]): Task components executed
- `execution_sequence` (List[FSAType]): FSA sequence used
- `results` (List[FSAExecutionResult]): Execution results

**Returns:** List of learned pattern descriptions

```python
patterns = orchestrator.learnFromExecution(
    task_components=components,
    execution_sequence=fsa_sequence,
    results=results
)

for pattern in patterns:
    print(f"• {pattern}")
```

### `getPerformanceDashboard()`

Get comprehensive performance dashboard across all FSAs.

**Returns:** Dashboard data with metrics for all FSAs

```python
dashboard = orchestrator.getPerformanceDashboard()

print(f"Total Orchestrations: {dashboard['total_orchestrations']}")

for fsa_name, metrics in dashboard['fsas'].items():
    print(f"\n{fsa_name}:")
    print(f"  Executions: {metrics['executions']}")
    print(f"  Avg Time: {metrics['avg_time_ms']:.1f}ms")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
```

## Task Types

| TaskType | Description | FSAs Used |
|----------|-------------|-----------|
| `PROJECT_BUILD` | Complete project generation | All FSAs (1.1 → 1.2 → 2.2 → 3.1 → 2.1 → 3.2) |
| `CODE_OPTIMIZATION` | Iterative code improvement | FSA-2.1, FSA-3.2 |
| `CODE_VALIDATION` | Code quality assessment | FSA-1.1, FSA-2.1 |
| `CODE_GENERATION` | Code generation | FSA-3.1, FSA-2.2 |
| `PROMPT_ANALYSIS` | Prompt optimization | FSA-1.1 |
| `TEMPLATE_RETRIEVAL` | Template lookup | FSA-1.2 |

## FSA Types

| FSAType | Component | Purpose |
|---------|-----------|---------|
| `PROMPT_OPTIMIZER` | FSA-1.1 | Optimize prompts for AI analysis |
| `TEMPLATE_LIBRARY` | FSA-1.2 | Retrieve code templates |
| `QUALITY_VALIDATOR` | FSA-2.1 | Validate code quality |
| `MODEL_ORCHESTRATOR` | FSA-2.2 | Route tasks to optimal models |
| `CODE_BUILDER` | FSA-3.1 | Multi-step code generation |
| `RSI_OPTIMIZER` | FSA-3.2 | Recursive self-improvement |

## Orchestration Result

The `OrchestrationResult` object contains:

```python
result = orchestrator.orchestrate(...)

# Execution details
result.success                  # True if all FSAs succeeded
result.task_components          # List of TaskComponent objects
result.execution_sequence       # Ordered FSA types executed
result.results                  # List of FSAExecutionResult objects
result.total_time_ms           # Total orchestration time
result.final_output            # Aggregated output from FSAs

# Metrics
result.metrics                 # Dict of aggregate metrics
result.learned_patterns        # List of learned pattern descriptions
```

## FSA Execution Result

Each FSA execution records:

```python
exec_result = result.results[0]

exec_result.fsa_type           # FSAType enum
exec_result.success            # True/False
exec_result.output             # FSA-specific output
exec_result.execution_time_ms  # Execution time
exec_result.metrics            # FSA-specific metrics
exec_result.error              # Error message if failed
```

## Examples

### Example 1: Complete Project Build

```python
from agno.meta import MetaFSAOrchestrator, TaskType

orchestrator = MetaFSAOrchestrator()

result = orchestrator.orchestrate(
    task="""
    Build a production REST API with:
    - User registration with email validation
    - Login with JWT tokens
    - Password hashing with bcrypt
    - Input validation and sanitization
    - Error handling and logging
    - Parameterized database queries
    """,
    task_type=TaskType.PROJECT_BUILD,
    language="python",
    config={
        "budget": {"max_cost_usd": 1.0, "max_latency_ms": 5000},
        "quality_target": 95.0,
        "rsi_iterations": 3
    }
)

print(f"Success: {result.success}")
print(f"FSA Chain: {' → '.join([fsa.value for fsa in result.execution_sequence])}")
print(f"Time: {result.total_time_ms:.0f}ms")

# Access final code
if hasattr(result.final_output, 'optimized_code'):
    print("\nGenerated Code:")
    print(result.final_output.optimized_code)
```

### Example 2: Code Optimization

```python
orchestrator = MetaFSAOrchestrator()

insecure_code = '''
def authenticate(username, password):
    query = "SELECT * FROM users WHERE username='" + username + "'"
    result = eval(query)
    return result
'''

result = orchestrator.orchestrate(
    task=insecure_code,
    task_type=TaskType.CODE_OPTIMIZATION,
    language="python",
    config={"rsi_iterations": 5}
)

print(f"Quality: {result.final_output.original_quality:.1f} → {result.final_output.final_quality:.1f}")
print(f"Improvement: {result.final_output.total_improvement:+.1f} points")
print(f"\nOptimized Code:")
print(result.final_output.optimized_code)
```

### Example 3: Code Validation

```python
orchestrator = MetaFSAOrchestrator()

code = '''
def process_payment(card_number, amount):
    api_key = "sk_live_secret_key"
    response = requests.post(
        "https://api.stripe.com/v1/charges",
        data={"amount": amount, "source": card_number}
    )
    return response.json()
'''

result = orchestrator.orchestrate(
    task=code,
    task_type=TaskType.CODE_VALIDATION,
    language="python"
)

validation = result.final_output
print(f"Quality Score: {validation.report.overall_score}/100")

print("\nDimension Scores:")
for dim, score in validation.report.dimensions.items():
    print(f"  {dim}: {score.score}/100")

print(f"\nIssues Found: {len(validation.all_issues)}")
for issue in validation.top_issues[:5]:
    print(f"  [{issue.severity.value}] {issue.message}")
```

### Example 4: Performance Dashboard

```python
orchestrator = MetaFSAOrchestrator()

# Run multiple orchestrations
tasks = [
    ("Build auth API", TaskType.PROJECT_BUILD),
    ("Optimize code", TaskType.CODE_OPTIMIZATION),
    ("Validate code", TaskType.CODE_VALIDATION)
]

for task, task_type in tasks:
    orchestrator.orchestrate(task, task_type, "python")

# Get performance insights
dashboard = orchestrator.getPerformanceDashboard()

print(f"Total Orchestrations: {dashboard['total_orchestrations']}")
print(f"\nFSA Performance:")

for fsa_name, metrics in dashboard['fsas'].items():
    if metrics['executions'] > 0:
        print(f"\n{fsa_name}:")
        print(f"  Executions: {metrics['executions']}")
        print(f"  Avg Time: {metrics['avg_time_ms']:.1f}ms")
        print(f"  Success Rate: {metrics['success_rate']:.1f}%")
```

### Example 5: Meta-Learning

```python
orchestrator = MetaFSAOrchestrator()

# Run orchestrations to build learning history
for i in range(5):
    result = orchestrator.orchestrate(
        task=f"Build API endpoint {i}",
        task_type=TaskType.PROJECT_BUILD,
        language="python"
    )

# Access learned patterns
print(f"Patterns Learned: {len(orchestrator.learned_patterns)}")

for pattern in orchestrator.learned_patterns:
    if pattern.get('type') == 'successful_chain':
        chain = ' → '.join(pattern['sequence'])
        print(f"Successful Chain: {chain}")
        print(f"  Avg Time: {pattern['avg_time_ms']:.0f}ms")
```

## Running the Demo

```bash
python cookbook/meta/meta_demo.py
```

**7 Comprehensive Demos:**
1. **Complete Project Build** - Full FSA chain execution
2. **Code Optimization** - RSI-focused workflow
3. **Code Validation** - Quality validation workflow
4. **Parallel Orchestrations** - Multiple concurrent tasks
5. **Meta-Learning** - Learning from execution history
6. **Performance Comparison** - Orchestrated vs direct FSA usage
7. **Error Handling** - Graceful failure and recovery

## Sample Output

```
================================================================================
  META-FSA ORCHESTRATION: PROJECT_BUILD
================================================================================

Task: Build production REST API with authentication
Language: python
Config: {'budget': {'max_cost_usd': 1.0}, 'quality_target': 95.0}

📋 Step 1: Task Decomposition
   Decomposed into 5 components

🔍 Step 2: FSA Selection
   Selected FSA chain: fsa_1_1 → fsa_1_2 → fsa_2_2 → fsa_3_1 → fsa_2_1 → fsa_3_2

⚙️  Step 3: FSA Chain Execution
   [1/6] Executing fsa_1_1...
      ✓ Completed in 12.3ms
   [2/6] Executing fsa_1_2...
      ✓ Completed in 8.1ms
   [3/6] Executing fsa_2_2...
      ✓ Completed in 5.2ms
   [4/6] Executing fsa_3_1...
      ✓ Completed in 156.7ms
   [5/6] Executing fsa_2_1...
      ✓ Completed in 23.4ms
   [6/6] Executing fsa_3_2...
      ✓ Completed in 89.2ms

✅ Orchestration complete in 295ms

================================================================================
  ORCHESTRATION SUMMARY
================================================================================

✅ Status: SUCCESS
📊 Total Time: 295ms
🔗 FSA Chain: fsa_1_1 → fsa_1_2 → fsa_2_2 → fsa_3_1 → fsa_2_1 → fsa_3_2
📋 Components: 5

📈 FSA Execution Results:
   [1] ✓ fsa_1_1: 12.3ms
       • prompt_length: 245
   [2] ✓ fsa_1_2: 8.1ms
       • template_count: 4
   [3] ✓ fsa_2_2: 5.2ms
       • model_selected: sonnet
   [4] ✓ fsa_3_1: 156.7ms
       • steps_completed: 7
       • overall_quality: 97.1
   [5] ✓ fsa_2_1: 23.4ms
       • quality_score: 97.1
       • issues_found: 2
   [6] ✓ fsa_3_2: 89.2ms
       • iterations: 2
       • quality_improvement: 2.9

🎓 Learned Patterns:
   • Successful FSA chain: fsa_1_1 → fsa_1_2 → fsa_2_2 → fsa_3_1 → fsa_2_1 → fsa_3_2
```

## Performance Dashboard

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     META-FSA PERFORMANCE DASHBOARD                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 Overall Statistics
├─ Total Orchestrations:  12
├─ FSAs Tracked:          6
└─ Patterns Learned:      8

🔧 FSA Performance Metrics

├─ FSA_1_1 (PROMPT OPTIMIZER)
│  ├─ Executions:     10
│  ├─ Avg Time:       11.2ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     112.0ms

├─ FSA_1_2 (TEMPLATE LIBRARY)
│  ├─ Executions:     10
│  ├─ Avg Time:       7.8ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     78.0ms

├─ FSA_2_1 (QUALITY VALIDATOR)
│  ├─ Executions:     12
│  ├─ Avg Time:       24.5ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     294.0ms

├─ FSA_2_2 (MODEL ORCHESTRATOR)
│  ├─ Executions:     8
│  ├─ Avg Time:       5.3ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     42.4ms

├─ FSA_3_1 (CODE BUILDER)
│  ├─ Executions:     8
│  ├─ Avg Time:       158.3ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     1266.4ms

├─ FSA_3_2 (RSI OPTIMIZER)
│  ├─ Executions:     7
│  ├─ Avg Time:       92.1ms
│  ├─ Success Rate:   100.0%
│  └─ Total Time:     644.7ms
```

## Best Practices

1. **Use Appropriate Task Types** - Choose the right TaskType for your use case
2. **Set Realistic Budgets** - Configure budget constraints appropriately
3. **Monitor Performance** - Use getPerformanceDashboard() regularly
4. **Review Learned Patterns** - Leverage meta-learning insights
5. **Handle Errors Gracefully** - Check result.success before accessing output
6. **Batch Similar Tasks** - Run multiple orchestrations to build learning history

## Integration with FSA Ecosystem

### Complete FSA Chain

```
FSA-1.1 (Prompt Optimizer)
  ↓
FSA-1.2 (Template Library)
  ↓
FSA-2.2 (Model Orchestrator)
  ↓
FSA-3.1 (Code Builder)
  ↓
FSA-2.1 (Quality Validator)
  ↓
FSA-3.2 (RSI Optimizer)
  ↓
Final Optimized Code
```

### Data Flow

```
User Task
  → Task Decomposition
    → FSA Selection (dependency resolution)
      → FSA-1.1: Optimized Prompts
        → FSA-1.2: Retrieved Templates
          → FSA-2.2: Model Routing
            → FSA-3.1: Generated Code
              → FSA-2.1: Quality Report
                → FSA-3.2: Optimized Code
                  → Final Result
```

## Architecture

```
MetaFSAOrchestrator
├── orchestrate() [Main Entry Point]
│   ├── decompose() → TaskComponent[]
│   ├── selectFSAs() → FSAType[]
│   ├── executeSequence() → FSAExecutionResult[]
│   ├── _aggregateOutput() → Final Output
│   └── learnFromExecution() → Patterns
│
├── FSA Instances
│   ├── FSA-1.1: PromptOptimizer
│   ├── FSA-1.2: CodeTemplateLibrary
│   ├── FSA-2.1: CodeQualityValidator
│   ├── FSA-2.2: MultiModelOrchestrator
│   ├── FSA-3.1: MultiStepCodeBuilder
│   └── FSA-3.2: RSICodeOptimizer
│
├── Performance Tracking
│   ├── trackPerformance()
│   ├── FSANode metrics
│   └── getPerformanceDashboard()
│
└── Meta-Learning
    ├── execution_history[]
    ├── learned_patterns[]
    └── learnFromExecution()
```

## Future Enhancements

- **Parallel FSA Execution** - Execute independent FSAs concurrently
- **Adaptive FSA Selection** - ML-based FSA chain optimization
- **Cost Optimization** - Multi-objective optimization (cost/quality/speed)
- **Custom FSA Plugins** - Support for user-defined FSA components
- **Distributed Execution** - FSA execution across multiple machines
- **Real-time Monitoring** - Live dashboard for orchestration progress

## License

Same as the parent Agno project.

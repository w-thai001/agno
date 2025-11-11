# FSA-2.2: Multi-Model Orchestrator

Intelligent routing and orchestration system for Claude models (Opus, Sonnet, Haiku) with automatic cost optimization and performance tracking.

## Features

- **Intelligent Task Routing**: Automatically analyzes task complexity and routes to optimal model
- **Cost Optimization**: Minimize costs while maintaining quality through smart model selection
- **Budget Constraints**: Support for cost, latency, speed, and quality preferences
- **Performance Tracking**: Comprehensive analytics and metrics for all executed tasks
- **Multi-Model Support**:
  - Claude Opus 4 (Highest capability, complex reasoning)
  - Claude Sonnet 4 (Balanced performance and cost)
  - Claude Haiku 3.5 (Fastest, most cost-effective)

## Installation

```bash
pip install agno anthropic
```

## Quick Start

```python
from agno.orchestrator import MultiModelOrchestrator
from agno.orchestrator.multi_model import BudgetConstraints

# Initialize orchestrator
orchestrator = MultiModelOrchestrator(enable_tracking=True)

# Simple task (will route to Haiku)
result = orchestrator.routeTask(
    "What is the capital of France?",
    execute=True
)

# Complex task (will route to Opus)
result = orchestrator.routeTask(
    "Design a distributed system architecture for real-time analytics...",
    budget=BudgetConstraints(prefer_quality=True),
    execute=True
)

# Get performance analytics
analytics = orchestrator.trackPerformance()
print(f"Total cost: ${analytics['total_cost_usd']:.6f}")
print(f"Average latency: {analytics['avg_latency_ms']:.0f}ms")

# Get cost savings report
savings = orchestrator.get_cost_savings_report()
print(f"Saved ${savings['savings_usd']:.6f} vs. using Opus for all tasks")
```

## Core Methods

### `routeTask(task, budget, context, execute)`

Routes a task to the optimal model and optionally executes it.

**Parameters:**
- `task` (str): The task/prompt to execute
- `budget` (BudgetConstraints, optional): Budget constraints
- `context` (dict, optional): Additional context for complexity analysis
- `execute` (bool): Whether to execute or just return routing decision

**Returns:** Dictionary with routing decision and execution results

### `selectModel(complexity, latency, budget)`

Selects the optimal model based on complexity and constraints.

**Parameters:**
- `complexity` (float): Task complexity score (0-10)
- `latency` (float, optional): Maximum acceptable latency in ms
- `budget` (BudgetConstraints, optional): Budget constraints

**Returns:** ModelConfig for the selected model

### `trackPerformance()`

Returns comprehensive performance analytics.

**Returns:** Dictionary with:
- Total tasks executed
- Success rate
- Cost metrics
- Latency statistics
- Per-model distribution and stats

## Budget Constraints

Control routing behavior with `BudgetConstraints`:

```python
from agno.orchestrator.multi_model import BudgetConstraints

# Optimize for speed
budget = BudgetConstraints(prefer_speed=True)

# Optimize for quality
budget = BudgetConstraints(prefer_quality=True)

# Set cost limit
budget = BudgetConstraints(max_cost_per_task=0.01)  # USD

# Set latency limit
budget = BudgetConstraints(max_latency_ms=500)  # milliseconds
```

## Model Characteristics

| Model | Complexity Score | Speed Score | Cost/1K Input | Cost/1K Output |
|-------|-----------------|-------------|---------------|----------------|
| **Opus** | 10/10 | 6/10 | $15.00 | $75.00 |
| **Sonnet** | 8/10 | 8/10 | $3.00 | $15.00 |
| **Haiku** | 6/10 | 10/10 | $0.80 | $4.00 |

## Task Complexity Analysis

The orchestrator automatically analyzes task complexity based on:

- Task length and structure
- Complexity indicators (reasoning, analysis, design, etc.)
- Simplicity indicators (quick, simple, list, etc.)
- Context hints (token estimates, tool requirements, multi-turn)

**Complexity Scoring:**
- 0-3: Simple tasks → Haiku
- 4-7: Balanced tasks → Sonnet
- 8-10: Complex tasks → Opus

## Examples

### Example 1: Simple Task (Haiku)
```python
orchestrator = MultiModelOrchestrator()
result = orchestrator.routeTask("What is Python?", execute=True)
# Routes to: Haiku (fast, low cost)
```

### Example 2: Complex Reasoning (Opus)
```python
result = orchestrator.routeTask(
    """Design a comprehensive multi-region cybersecurity architecture
    with zero-trust, AI-powered threat detection, and compliance...""",
    budget=BudgetConstraints(prefer_quality=True),
    execute=True
)
# Routes to: Opus (maximum capability)
```

### Example 3: Balanced Task (Sonnet)
```python
result = orchestrator.routeTask(
    "Explain REST vs GraphQL with code examples",
    execute=True
)
# Routes to: Sonnet (balanced)
```

### Example 4: Budget Optimization
```python
# Speed priority
result = orchestrator.routeTask(
    task,
    budget=BudgetConstraints(prefer_speed=True)
)

# Cost constraint
result = orchestrator.routeTask(
    task,
    budget=BudgetConstraints(max_cost_per_task=0.01)
)
```

## Performance Tracking

Track and analyze performance across all tasks:

```python
analytics = orchestrator.trackPerformance()

print(f"Tasks executed: {analytics['total_tasks']}")
print(f"Success rate: {analytics['success_rate']*100}%")
print(f"Total cost: ${analytics['total_cost_usd']}")
print(f"Avg latency: {analytics['avg_latency_ms']}ms")

# Per-model statistics
for model, stats in analytics['model_stats'].items():
    print(f"{model}: {stats['tasks']} tasks, ${stats['total_cost_usd']}")
```

## Cost Savings Analysis

```python
savings = orchestrator.get_cost_savings_report()
print(f"Intelligent routing cost: ${savings['actual_cost_usd']}")
print(f"Opus-only cost: ${savings['opus_only_cost_usd']}")
print(f"Savings: {savings['savings_percent']}%")
```

## Running the Demo

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key"

# Run the comprehensive demo
python cookbook/orchestrator/multi_model_demo.py
```

The demo showcases:
1. Simple task routing (Haiku)
2. Complex reasoning task (Opus)
3. Balanced task (Sonnet)
4. Budget optimization scenarios
5. Performance tracking and analytics
6. Cost savings analysis

## Architecture

```
MultiModelOrchestrator
├── Task Analysis
│   └── analyze_task_complexity()
├── Model Selection
│   └── selectModel()
├── Task Routing & Execution
│   └── routeTask()
└── Performance Tracking
    ├── trackPerformance()
    └── get_cost_savings_report()
```

## Error Handling

The orchestrator includes comprehensive error handling:
- API connection errors
- Rate limiting with automatic retry
- Invalid API keys
- Model availability issues
- Budget constraint violations

All errors are logged and included in task metrics for analysis.

## Best Practices

1. **Enable tracking** for production use to monitor costs and performance
2. **Set budget constraints** to prevent cost overruns
3. **Use context hints** to improve complexity analysis accuracy
4. **Monitor analytics** regularly to optimize routing decisions
5. **Review cost savings** to validate orchestration effectiveness

## License

Same as the parent Agno project.

# FSA-4.1: Meta-FSA Orchestrator

The Meta-FSA Orchestrator is a master coordinator that intelligently routes tasks through optimal FSA (Functional Specific Agent) chains based on task characteristics, complexity, and historical performance data.

## Overview

The Meta-FSA Orchestrator provides:

- **Intelligent Task Analysis**: Automatically detects complexity, task type, quality requirements, and optimization needs
- **Dynamic FSA Routing**: Selects optimal FSA chains based on task profiles
- **Sequential Execution**: Executes FSA pipelines with context passing between stages
- **Meta-Learning**: Learns from execution patterns to improve future routing decisions
- **Performance Tracking**: Comprehensive analytics and performance metrics

## FSA Modules

### Tier 1: Planning & Decomposition
- **FSA-1.1**: Task Planning Agent - Analyzes tasks and creates execution plans
- **FSA-1.2**: Task Decomposition Agent - Breaks down tasks into manageable subtasks

### Tier 2: Implementation & Quality
- **FSA-2.1**: Quality Assurance Agent - Performs validation and quality checks
- **FSA-2.2**: Implementation Agent - Executes main implementation work

### Tier 3: Integration & Optimization
- **FSA-3.1**: Integration Agent - Handles integration and coordination
- **FSA-3.2**: Optimization Agent - Performs performance optimization

## Quick Start

```python
from agno.fsa.mock_fsas import FSA_1_1, FSA_1_2, FSA_2_1, FSA_2_2, FSA_3_1, FSA_3_2
from agno.fsa.orchestrator import MetaFSAOrchestrator

# Initialize FSA modules
fsa_1_1 = FSA_1_1()
fsa_1_2 = FSA_1_2()
fsa_2_1 = FSA_2_1()
fsa_2_2 = FSA_2_2()
fsa_3_1 = FSA_3_1()
fsa_3_2 = FSA_3_2()

# Initialize orchestrator
orchestrator = MetaFSAOrchestrator(
    fsa_1_1=fsa_1_1,
    fsa_1_2=fsa_1_2,
    fsa_2_1=fsa_2_1,
    fsa_2_2=fsa_2_2,
    fsa_3_1=fsa_3_1,
    fsa_3_2=fsa_3_2
)

# Define a task
task = {
    "description": "Build REST API with authentication",
    "requirements": ["CRUD operations", "Authentication"]
}

# Orchestrate the task
result = orchestrator.orchestrate(task)

# View results
print(f"Selected Chain: {' → '.join(result['selected_chain'])}")
print(f"Execution Time: {result['total_execution_time']:.4f}s")
print(f"Success Rate: {result['execution_result']['successful_fsas']}/{result['execution_result']['fsa_count']}")

# Get analytics
analytics = orchestrator.getAnalytics()
print(f"Total Executions: {analytics['summary']['total_executions']}")
```

## Core API

### MetaFSAOrchestrator

#### `__init__(fsa_1_1, fsa_1_2, fsa_2_1, fsa_2_2, fsa_3_1, fsa_3_2)`

Initialize the orchestrator with all FSA dependencies. All parameters are required and must not be None.

**Parameters:**
- `fsa_1_1`: Task Planning Agent (FSA-1.1)
- `fsa_1_2`: Task Decomposition Agent (FSA-1.2)
- `fsa_2_1`: Quality Assurance Agent (FSA-2.1)
- `fsa_2_2`: Implementation Agent (FSA-2.2)
- `fsa_3_1`: Integration Agent (FSA-3.1)
- `fsa_3_2`: Optimization Agent (FSA-3.2)

**Raises:**
- `ValueError`: If any FSA module is None

#### `orchestrate(task, options=None)`

Main orchestration method that analyzes tasks and routes through optimal FSA chains.

**Parameters:**
- `task` (dict): Task specification containing description and requirements
- `options` (dict, optional): Configuration options
  - `force_chain` (list): Force a specific FSA chain (bypasses intelligent selection)

**Returns:**
- `dict`: Orchestration result containing:
  - `status`: Execution status ("success" or "error")
  - `task_profile`: Task analysis results
  - `selected_chain`: List of FSA names in execution order
  - `execution_result`: Results from FSA chain execution
  - `total_execution_time`: Total execution time in seconds
  - `timestamp`: ISO format timestamp

#### `analyzeTask(task)`

Analyze task complexity, type, quality requirements, and optimization needs.

**Parameters:**
- `task` (dict): Task specification

**Returns:**
- `dict`: Task profile containing:
  - `complexity`: "low", "medium", or "high"
  - `task_type`: "backend", "frontend", "data", "testing", or "general"
  - `quality_requirements`: Dict of quality requirement flags
  - `optimization_needs`: Dict of optimization requirement flags
  - `integration_requirements`: Dict of integration requirement flags
  - `original_task`: Original task specification

#### `selectFSAChain(profile, options=None)`

Select optimal FSA sequence based on task profile.

**Parameters:**
- `profile` (dict): Task profile from analyzeTask
- `options` (dict, optional): Configuration options

**Returns:**
- `list`: List of FSA names in execution order

#### `executeFSAChain(chain, task, options=None)`

Execute FSA pipeline sequentially.

**Parameters:**
- `chain` (list): List of FSA names to execute in order
- `task` (dict): Task specification
- `options` (dict, optional): Execution options

**Returns:**
- `dict`: Execution results containing:
  - `chain`: Executed FSA chain
  - `results`: List of individual FSA results
  - `total_execution_time`: Total chain execution time
  - `fsa_count`: Number of FSAs in chain
  - `successful_fsas`: Number of successfully executed FSAs
  - `final_context`: Final execution context

#### `learnFromExecution(profile, chain, result, execution_time)`

Meta-learning from execution patterns. Updates performance statistics and learning data.

**Parameters:**
- `profile` (dict): Task profile
- `chain` (list): FSA chain that was executed
- `result` (dict): Execution result
- `execution_time` (float): Total execution time

#### `getAnalytics()`

Return performance history and learning data.

**Returns:**
- `dict`: Comprehensive analytics containing:
  - `performance_stats`: Overall performance statistics
  - `execution_history`: List of all execution records
  - `learning_data`: Meta-learning data and optimal chains
  - `fsa_stats`: Individual FSA statistics
  - `summary`: High-level summary metrics

## Intelligence Features

### Complexity Detection

The orchestrator analyzes task descriptions and automatically detects complexity levels:

- **Low**: Simple, single-purpose tasks (e.g., utility functions, helpers)
- **Medium**: Multi-component tasks (e.g., REST APIs, CRUD operations)
- **High**: Complex systems (e.g., microservices, distributed systems)

Indicators include specific keywords, task structure, and explicit complexity specifications.

### Task Type Detection

Automatically identifies task types to optimize FSA selection:

- **Backend**: API, server-side, database operations
- **Frontend**: UI, components, client-side
- **Data**: Analytics, ETL, data processing
- **Testing**: Test suites, integration tests
- **General**: Generic or unspecified tasks

### Dynamic Routing

FSA chains are dynamically constructed based on:

1. **Complexity Level**: Higher complexity adds more FSAs
2. **Requirements**: Integration and optimization needs add specialized FSAs
3. **Historical Performance**: Learned optimal chains influence selection
4. **Task Type**: Certain types prefer specific FSA sequences

### Meta-Learning

The orchestrator learns from each execution:

- Tracks performance by complexity, task type, and chain
- Identifies optimal chains for specific task profiles
- Maintains success rates and execution times
- Adapts future routing based on historical data

## Example Routing Patterns

### Simple Task
```
Task: "Create a utility function"
Complexity: low
Chain: FSA-1.1 → FSA-1.2 → FSA-2.1
Reasoning: Minimal pipeline for straightforward tasks
```

### Medium Complexity
```
Task: "Build REST API with multiple endpoints"
Complexity: medium
Chain: FSA-1.1 → FSA-1.2 → FSA-2.2 → FSA-3.1 → FSA-2.1
Reasoning: Adds implementation (2.2) and integration (3.1) for multi-component work
```

### Complex with Optimization
```
Task: "Create distributed system with performance optimization"
Complexity: high
Chain: FSA-1.1 → FSA-1.2 → FSA-2.2 → FSA-3.1 → FSA-3.2 → FSA-2.1
Reasoning: Full pipeline including optimization (3.2) for complex systems
```

## Running Tests

Run the comprehensive test suite to see all routing patterns in action:

```bash
cd libs/agno
python -m agno.fsa.test_orchestrator
```

The test suite demonstrates:
1. Simple task routing
2. Medium complexity routing
3. Complex task with optimization routing
4. Performance tracking and meta-learning
5. Comparative analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Meta-FSA Orchestrator                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Analyze    │→ │   Select     │→ │   Execute    │      │
│  │     Task     │  │  FSA Chain   │  │  FSA Chain   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↓                  ↓             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             Meta-Learning & Analytics                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │            FSA Registry                    │
        ├───────────────────────────────────────────┤
        │  FSA-1.1: Planning                        │
        │  FSA-1.2: Decomposition                   │
        │  FSA-2.1: Quality Assurance               │
        │  FSA-2.2: Implementation                  │
        │  FSA-3.1: Integration                     │
        │  FSA-3.2: Optimization                    │
        └───────────────────────────────────────────┘
```

## Module Export

The orchestrator is exported as a CommonJS-compatible module:

```python
# Direct import
from agno.fsa.orchestrator import MetaFSAOrchestrator

# Package-level import
from agno.fsa import MetaFSAOrchestrator
```

## Defensive Programming

All methods include defensive null checks:

- Constructor validates all FSA dependencies
- Methods validate input parameters
- Execution errors are caught and handled gracefully
- Analytics methods handle missing or incomplete data

## Performance Considerations

- FSA execution is sequential (not parallel) to maintain context flow
- Learning data grows with each execution (consider periodic cleanup for long-running systems)
- Task analysis uses regex and keyword matching (optimized for performance)
- Analytics retrieval is O(1) for summary data, O(n) for full history

## Future Enhancements

Potential improvements for future versions:

1. **Parallel FSA Execution**: Execute independent FSAs in parallel
2. **Chain Optimization**: Use machine learning to optimize chain selection
3. **Custom FSA Plugins**: Allow custom FSA modules to be registered
4. **Persistent Learning**: Save/load learning data across sessions
5. **Real-time Monitoring**: Dashboard for live orchestration monitoring
6. **A/B Testing**: Compare different routing strategies

## License

Part of the Agno framework.

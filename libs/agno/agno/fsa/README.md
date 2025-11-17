# Dependency Optimizer FSA

A production-ready Finite State Automaton (FSA) for analyzing and optimizing dependency graphs in task execution, build pipelines, and orchestration systems.

## Overview

The Dependency Optimizer FSA provides a robust solution for managing complex dependency relationships between tasks, detecting circular dependencies, optimizing execution order, and identifying opportunities for parallel execution.

## Features

- **Dependency Graph Construction**: Build complex dependency graphs with nodes and edges
- **Circular Dependency Detection**: Automatically detect and report circular dependencies with full path tracing
- **Topological Sorting**: Generate optimal execution order respecting all dependencies
- **Graph Optimization**: Remove redundant transitive dependencies
- **Parallel Execution Analysis**: Identify groups of tasks that can run in parallel
- **Critical Path Analysis**: Find the longest dependency chain (bottleneck)
- **FSA State Machine**: Clear state transitions (IDLE, BUILDING, VALIDATING, OPTIMIZING, ANALYZING, ERROR)
- **Comprehensive Statistics**: Get detailed metrics about your dependency graph

## Installation

The FSA is included in the `agno` package:

```python
from agno.fsa import DependencyOptimizerFSA, DependencyNode, DependencyEdge, FSAState
```

## Quick Start

```python
from agno.fsa import DependencyOptimizerFSA

# Create FSA instance
fsa = DependencyOptimizerFSA()

# Add tasks
fsa.add_node("compile", "Compile Code")
fsa.add_node("test", "Run Tests")
fsa.add_node("package", "Package Application")
fsa.add_node("deploy", "Deploy to Production")

# Define dependencies (task -> depends_on)
fsa.add_dependency("test", "compile")
fsa.add_dependency("package", "test")
fsa.add_dependency("deploy", "package")

# Validate graph
if fsa.validate_graph():
    print("✓ Graph is valid")

    # Get execution order
    order = fsa.get_execution_order()
    print(f"Execution order: {order}")
    # Output: ['compile', 'test', 'package', 'deploy']

    # Find parallel execution opportunities
    groups = fsa.find_parallel_groups()
    print(f"Parallel groups: {groups}")

    # Get critical path
    critical = fsa.get_critical_path()
    print(f"Critical path: {critical}")
else:
    print(f"✗ Graph invalid: {fsa.error_message}")
```

## API Reference

### DependencyOptimizerFSA

#### Methods

##### `add_node(node_id: str, name: str, metadata: Optional[Dict] = None)`
Add a node to the dependency graph.

```python
fsa.add_node("task1", "My Task", metadata={"priority": "high"})
```

##### `add_dependency(node: str, depends_on: str, weight: float = 1.0)`
Add a dependency relationship. The `node` depends on `depends_on`.

```python
fsa.add_dependency("test", "build", weight=2.0)
```

##### `validate_graph() -> bool`
Validate the graph for circular dependencies and conflicts. Returns `True` if valid.

```python
if fsa.validate_graph():
    print("Graph is valid")
else:
    print(f"Error: {fsa.error_message}")
```

##### `get_execution_order() -> List[str]`
Get topologically sorted execution order.

```python
order = fsa.get_execution_order()
# Returns: ['task1', 'task2', 'task3', ...]
```

##### `optimize_graph() -> int`
Remove redundant transitive dependencies. Returns number of edges removed.

```python
removed_count = fsa.optimize_graph()
print(f"Removed {removed_count} redundant dependencies")
```

##### `find_parallel_groups() -> List[List[str]]`
Identify nodes that can execute in parallel.

```python
groups = fsa.find_parallel_groups()
# Returns: [['task1', 'task2'], ['task3'], ['task4', 'task5']]
# task1 and task2 can run in parallel (stage 1)
# task3 must run after (stage 2)
# task4 and task5 can run in parallel (stage 3)
```

##### `get_critical_path() -> List[str]`
Get the longest dependency chain (critical path).

```python
path = fsa.get_critical_path()
# Returns: ['start', 'middle1', 'middle2', 'end']
```

##### `get_stats() -> Dict[str, Any]`
Get comprehensive statistics about the graph.

```python
stats = fsa.get_stats()
# Returns dict with: node_count, edge_count, avg_in_degree,
# max_in_degree, source_nodes, sink_nodes, parallel_groups_count,
# max_parallelism, critical_path_length, etc.
```

##### `reset()`
Reset the FSA to initial state, clearing all data.

```python
fsa.reset()
```

### FSA States

- **IDLE**: Ready for operations
- **BUILDING**: Adding nodes and edges
- **VALIDATING**: Checking for circular dependencies
- **OPTIMIZING**: Removing redundant edges
- **ANALYZING**: Computing critical path or parallel groups
- **ERROR**: Invalid operation or graph state

## Use Cases

### 1. Build Pipeline Optimization

```python
fsa = DependencyOptimizerFSA()

# Define build stages
fsa.add_node("setup", "Setup Environment")
fsa.add_node("deps", "Install Dependencies")
fsa.add_node("lint", "Lint Code")
fsa.add_node("test", "Run Tests")
fsa.add_node("build", "Build Application")
fsa.add_node("deploy", "Deploy")

# Define dependencies
fsa.add_dependency("deps", "setup")
fsa.add_dependency("lint", "deps")
fsa.add_dependency("test", "deps")
fsa.add_dependency("build", "lint")
fsa.add_dependency("build", "test")
fsa.add_dependency("deploy", "build")

# Find parallel opportunities
groups = fsa.find_parallel_groups()
# Stage 1: setup
# Stage 2: deps
# Stage 3: lint, test (can run in parallel!)
# Stage 4: build
# Stage 5: deploy
```

### 2. Microservice Deployment

```python
fsa = DependencyOptimizerFSA()

# Infrastructure
fsa.add_node("vpc", "Create VPC")
fsa.add_node("db", "Deploy Database")
fsa.add_node("cache", "Deploy Cache")

# Services
fsa.add_node("auth", "Auth Service")
fsa.add_node("api", "API Service")
fsa.add_node("web", "Web Frontend")

# Dependencies
fsa.add_dependency("db", "vpc")
fsa.add_dependency("cache", "vpc")
fsa.add_dependency("auth", "db")
fsa.add_dependency("api", "auth")
fsa.add_dependency("api", "cache")
fsa.add_dependency("web", "api")

# Get deployment order
order = fsa.get_execution_order()
critical_path = fsa.get_critical_path()
```

### 3. Data Pipeline Processing

```python
fsa = DependencyOptimizerFSA()

# Data processing stages
fsa.add_node("extract", "Extract Raw Data")
fsa.add_node("clean", "Clean Data")
fsa.add_node("transform", "Transform Data")
fsa.add_node("aggregate", "Aggregate Results")
fsa.add_node("load", "Load to Warehouse")

fsa.add_dependency("clean", "extract")
fsa.add_dependency("transform", "clean")
fsa.add_dependency("aggregate", "transform")
fsa.add_dependency("load", "aggregate")

# Optimize and execute
fsa.optimize_graph()
execution_plan = fsa.get_execution_order()
```

## Error Handling

The FSA provides comprehensive error handling:

```python
fsa = DependencyOptimizerFSA()

# Add nodes
fsa.add_node("A", "Task A")
fsa.add_node("B", "Task B")

# Try to add dependency to non-existent node
try:
    fsa.add_dependency("A", "NonExistent")
except ValueError as e:
    print(f"Error: {e}")

# Create circular dependency
fsa.add_dependency("B", "A")
fsa.add_dependency("A", "B")

if not fsa.validate_graph():
    print(f"Validation failed: {fsa.error_message}")
    print(f"FSA state: {fsa.state}")
    # Output: Circular dependency detected: A -> B -> A
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/unit/test_dependency_optimizer_fsa.py -v
```

Test coverage includes:
- Graph construction
- Cycle detection (including self-loops)
- Topological sorting
- Graph optimization
- Parallel group identification
- Critical path analysis
- State machine transitions
- Error handling
- Large graph performance

## Demo

Run the interactive demo to see real-world examples:

```bash
python examples/dependency_optimizer_demo.py
```

The demo showcases:
1. Build pipeline optimization with parallel execution
2. Circular dependency detection
3. Microservice deployment orchestration

## Performance

The FSA is optimized for production use:

- **Time Complexity**:
  - Add node/edge: O(1)
  - Cycle detection: O(V + E)
  - Topological sort: O(V + E)
  - Critical path: O(V + E)
  - Optimization: O(V * E)

- **Space Complexity**: O(V + E)

Where V = number of vertices (nodes) and E = number of edges (dependencies).

Tested with graphs up to 100+ nodes with excellent performance.

## Architecture

The FSA follows clean architecture principles:

1. **State Machine**: Clear state transitions with validation
2. **Type Safety**: Full type hints with dataclasses
3. **Error Handling**: Comprehensive error messages and state management
4. **Caching**: Results are cached until graph changes
5. **Logging**: Detailed logging for debugging
6. **Testing**: 25+ unit tests with high coverage

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- New features include tests
- Code follows existing patterns
- Documentation is updated

## License

Part of the Agno framework. See LICENSE for details.

## Author

Created for the w-thai001/agno repository.

# Constitutional Cognitive Meta-Framework (CCMF)

A comprehensive framework for building AI systems with constitutional principles, cognitive patterns, recursive self-improvement, and meta-learning capabilities.

## 🎯 Overview

The CCMF framework provides a complete ecosystem for developing AI systems that are:

- **Constitutional**: Governed by ethical principles and safety constraints
- **Cognitive**: Utilizing proven patterns for common operations
- **Self-Improving**: Continuously learning and adapting through RSI feedback loops
- **Meta-Learning**: Learning from past experiences to improve future performance

## 📦 Modules

### SESSION 1 - Core Framework

1. **ccmf_constitutional.py**
   - Constitutional framework with ethical principles
   - Compliance validation for all operations
   - Multiple principle categories (Safety, Ethics, Transparency, etc.)

2. **ccmf_patterns.py**
   - DirectPathAccessPattern: Direct file/resource access
   - KnownPathSearchPattern: Search in known locations
   - GitRepositoryFilePattern: Git-aware file operations
   - CheckpointRecoveryPattern: State checkpointing
   - GitStateAnalysisPattern: Comprehensive Git analysis
   - CompositeStateRecoveryPattern: Multi-source recovery

3. **ccmf_rsi_loop.py**
   - Recursive Self-Improvement feedback loop
   - Performance analysis and trend detection
   - Automatic adaptation strategies
   - Health monitoring and improvement cycles

4. **ccmf_workflows.py**
   - Workflow orchestration engine
   - Step dependency management
   - Constitutional validation integration
   - Error handling and retry mechanisms

5. **ccmf_meta_learning.py**
   - Meta-Learning Architecture (MLA)
   - Learning from past operations
   - Pattern recommendation system
   - MLA Leverage Quotient calculations

### SESSION 2 - Examples and Demo

6. **ccmf_examples.py**
   - Comprehensive examples for ALL patterns
   - Real-world usage demonstrations
   - Performance metrics and logging
   - Integration examples

7. **ccmf_demo.py**
   - Interactive CLI demonstration
   - Menu-driven interface
   - Colored output (with fallback)
   - Live pattern demonstrations

## 🚀 Quick Start

### Running the Interactive Demo

```bash
python ccmf_demo.py
```

The interactive demo provides:
- Pattern demonstrations
- Constitutional compliance validation
- RSI feedback loop visualization
- Meta-learning architecture showcase
- Integrated workflow examples

### Running Comprehensive Examples

```bash
python ccmf_examples.py
```

This runs all examples showcasing every pattern and capability.

### Using Patterns Programmatically

```python
from ccmf_patterns import DirectPathAccessPattern

# Create pattern instance
pattern = DirectPathAccessPattern()

# Execute operation
result = pattern.execute(path="/path/to/file", operation="exists")

# Check result
if result.success:
    print(f"File exists: {result.data}")
    print(f"Execution time: {result.execution_time}s")
```

## 📊 Key Features

### Constitutional Compliance

All operations can be validated against constitutional principles:

```python
from ccmf_constitutional import validate_operation

context = {
    'operation_type': 'file_read',
    'risk_assessment': 'low',
    'logging_enabled': True,
    'audit_trail': True,
    'error_handling': True,
    'recovery_strategy': 'retry_with_backoff',
    'data_classification': 'internal',
    'privacy_check': True,
    'ethical_review': True
}

report = validate_operation(context)
print(f"Compliance: {report.compliance_score:.2%}")
```

### RSI Feedback Loop

Continuous improvement through feedback:

```python
from ccmf_rsi_loop import RSIFeedbackLoop, FeedbackType

rsi = RSIFeedbackLoop()

# Collect feedback
rsi.collect_feedback(
    feedback_type=FeedbackType.SUCCESS,
    source="my_operation",
    metrics={'execution_time': 0.5, 'quality': 0.95}
)

# Run improvement cycle
cycle_result = rsi.run_improvement_cycle()
```

### Meta-Learning Architecture

Learn from past operations:

```python
from ccmf_meta_learning import MetaLearningArchitecture

mla = MetaLearningArchitecture()

# Record learning example
mla.record_example(
    pattern_name="DirectPathAccessPattern",
    context={'operation': 'read', 'size': 'small'},
    outcome={'status': 'success'},
    performance_metrics={'execution_time': 0.1, 'quality': 0.95},
    success=True
)

# Calculate leverage quotient
quotient = mla.calculate_leverage_quotient()
print(f"MLA Quotient: {quotient.overall_quotient:.4f}")
print(f"Grade: {quotient.get_grade()}")
```

### Workflow Orchestration

Build complex multi-step workflows:

```python
from ccmf_workflows import WorkflowBuilder
from ccmf_patterns import DirectPathAccessPattern

# Build workflow
workflow = WorkflowBuilder("my_workflow", "My Workflow")\
    .with_rsi(True)\
    .add_pattern_step(
        step_id="step1",
        name="Check File",
        pattern=DirectPathAccessPattern(),
        parameters={'path': '/path/to/file', 'operation': 'exists'}
    )\
    .build()

# Execute workflow
result = workflow.execute()
print(f"Status: {result['status']}")
```

## 🎓 Pattern Examples

### DirectPathAccessPattern

```python
from ccmf_patterns import DirectPathAccessPattern

pattern = DirectPathAccessPattern()

# Check existence
result = pattern.execute(path="file.txt", operation="exists")

# Get statistics
result = pattern.execute(path="file.txt", operation="stat")

# Read file
result = pattern.execute(path="file.txt", operation="read")
```

### KnownPathSearchPattern

```python
from ccmf_patterns import KnownPathSearchPattern

pattern = KnownPathSearchPattern()

# Search for files
result = pattern.execute(
    search_paths=["/path/to/search"],
    pattern="*.py",
    recursive=True
)

print(f"Found {len(result.data)} files")
```

### GitRepositoryFilePattern

```python
from ccmf_patterns import GitRepositoryFilePattern

pattern = GitRepositoryFilePattern()

# Get repository status
result = pattern.execute(repo_path="/path/to/repo", operation="status")

# Get commit log
result = pattern.execute(repo_path="/path/to/repo", operation="log", limit=10)

# Get diff
result = pattern.execute(repo_path="/path/to/repo", operation="diff")
```

### CheckpointRecoveryPattern

```python
from ccmf_patterns import CheckpointRecoveryPattern

pattern = CheckpointRecoveryPattern()

# Save checkpoint
state_data = {'model': 'state', 'iteration': 100}
result = pattern.execute(
    operation="save",
    checkpoint_id="my_checkpoint",
    state_data=state_data
)

# Load checkpoint
result = pattern.execute(
    operation="load",
    checkpoint_id="my_checkpoint"
)

# List checkpoints
result = pattern.execute(operation="list")
```

## 📈 Performance Metrics

The framework tracks comprehensive performance metrics:

- Execution times
- Success/failure rates
- Quality scores
- Resource usage
- Compliance scores
- Learning effectiveness

## 🔧 Requirements

- Python 3.8+
- Optional: colorama (for colored output in demo)

## 📝 License

See the main project LICENSE file.

## 🤝 Contributing

Contributions are welcome! Please see CONTRIBUTING.md in the main project.

## 📚 Documentation

For more detailed documentation, examples, and tutorials, see the full documentation.

## 🎯 Use Cases

- **AI System Development**: Build AI systems with ethical constraints
- **Workflow Automation**: Orchestrate complex multi-step operations
- **Self-Improving Systems**: Create systems that learn and adapt
- **Code Analysis**: Analyze and process code repositories
- **State Management**: Checkpoint and recover system state
- **Performance Optimization**: Continuously improve system performance

## 🌟 Highlights

### MLA Leverage Quotient

The Meta-Learning Architecture calculates a comprehensive leverage quotient that measures:
- Knowledge reuse rate
- Transfer learning effectiveness
- Average performance gain
- Overall learning effectiveness

Grades range from F (Poor) to A+ (Exceptional).

### Constitutional Compliance

All operations can be validated against multiple principle categories:
- Safety
- Ethics
- Transparency
- Efficiency
- Robustness
- Privacy

### RSI Feedback Loop

The framework includes a sophisticated feedback loop that:
- Collects feedback from all operations
- Analyzes performance trends
- Makes adaptation decisions
- Applies improvements automatically

---

**CCMF Version 1.0.0** - Built for production-ready AI systems with constitutional guarantees.

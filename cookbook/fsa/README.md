# FSA (Finite State Automaton) Framework Examples

Production-ready FSA framework for building sophisticated agentic systems with structured state management.

## 🎯 Overview

The Agno FSA framework provides **5 specialized FSAs** for complex development workflows:

1. **🎭 Meta-FSA Orchestrator** - Master coordinator for multiple FSAs
2. **🏗️ Multi-Step Code Builder** - Systematic code generation through structured phases
3. **📊 MLA Task Deconstructor** - Maximum Leverage Analysis for task prioritization
4. **⚡ RSI Code Optimizer** - Recursive Self-Improvement code optimization
5. **✅ Code Quality Validator** - Comprehensive code quality validation

## 📚 Examples

### Basic FSA Usage
- `01_basic_fsa_usage.py` - Introduction to FSA concepts and basic usage

### Individual FSAs
- `02_code_builder_example.py` - Build code through structured development phases
- `03_mla_task_deconstruction.py` - Deconstruct tasks with leverage analysis
- `04_code_optimizer.py` - Self-improving code optimization
- `05_meta_orchestrator.py` - Coordinate multiple FSAs in complex workflows
- `06_quality_validator.py` - Validate code quality and security

## 🚀 Quick Start

```python
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Create agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="Expert software engineer"
)

# Create code builder
builder = MultiStepCodeBuilder(
    name="FeatureBuilder",
    code_agent=agent
)

# Build feature
result = builder.run({
    "task": "Create a user authentication system",
    "language": "python"
})

print(f"Generated {len(result.artifacts)} artifacts")
```

## 🎯 Key Features

### Meta-FSA Orchestrator
- ✅ Parallel and sequential FSA execution
- ✅ Dependency management
- ✅ Intelligent task routing
- ✅ Failure handling and recovery
- ✅ Execution monitoring

### Multi-Step Code Builder
- ✅ Requirements analysis
- ✅ Design specification
- ✅ Progressive implementation
- ✅ Automated testing
- ✅ Documentation generation

### MLA Task Deconstructor
- ✅ Leverage-based prioritization (impact/effort)
- ✅ Atomic subtask generation
- ✅ Reusability identification
- ✅ Strategic optimization
- ✅ Dependency resolution

### RSI Code Optimizer
- ✅ Multi-dimensional optimization (performance, readability, complexity)
- ✅ Pattern learning from successful optimizations
- ✅ Self-improving heuristics
- ✅ Persistent knowledge base
- ✅ Validation of improvements

### Code Quality Validator
- ✅ Style and formatting checks
- ✅ Complexity analysis
- ✅ Security vulnerability scanning
- ✅ Test coverage validation
- ✅ Documentation completeness

## 📖 Documentation

For comprehensive documentation, see the main FSA module docstrings:

```python
from agno.fsa import (
    FSA,
    MetaFSAOrchestrator,
    MultiStepCodeBuilder,
    MLATaskDeconstructor,
    RSICodeOptimizer,
    CodeQualityValidator
)

help(MetaFSAOrchestrator)  # View detailed documentation
```

## 🎓 Learning Path

1. **Start with**: `01_basic_fsa_usage.py` - Learn FSA fundamentals
2. **Then try**: Individual FSA examples (02-06) - Explore each FSA's capabilities
3. **Advanced**: `05_meta_orchestrator.py` - Coordinate multiple FSAs

## 💡 Use Cases

### Automated Development Pipeline
```python
# 1. Deconstruct task → 2. Build code → 3. Optimize → 4. Validate
orchestrator.register_fsa(task_deconstructor)
orchestrator.register_fsa(code_builder, depends_on=[task_deconstructor.fsa_id])
orchestrator.register_fsa(optimizer, depends_on=[code_builder.fsa_id])
orchestrator.register_fsa(validator, depends_on=[optimizer.fsa_id])
```

### Continuous Code Improvement
```python
# Optimize and learn from patterns
optimizer = RSICodeOptimizer(enable_learning=True)
result = optimizer.run({"code": source_code})
optimizer.save_knowledge_base("patterns.json")
```

### Quality Assurance
```python
# Comprehensive validation
validator = CodeQualityValidator(
    min_overall_score=80.0,
    enable_security_scan=True
)
result = validator.run({"code": code, "tests": tests})
```

## 🔧 Configuration

Each FSA is highly configurable:

```python
# Code Builder Configuration
builder = MultiStepCodeBuilder(
    programming_language="python",
    framework="FastAPI",
    include_tests=True,
    code_style="pep8",
    min_test_coverage=0.8
)

# Optimizer Configuration
optimizer = RSICodeOptimizer(
    enable_learning=True,
    enable_self_improvement=True,
    min_improvement_threshold=5.0
)

# Validator Configuration
validator = CodeQualityValidator(
    min_overall_score=70.0,
    max_cyclomatic_complexity=10,
    style_guide="pep8"
)
```

## 🤝 Integration with Agno

FSAs integrate seamlessly with Agno's Agent system:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Create specialized agents
coding_agent = Agent(model=OpenAIChat(id="gpt-4o"),
                     description="Expert coder")

security_agent = Agent(model=OpenAIChat(id="gpt-4o"),
                       description="Security expert")

# Use with FSAs
builder = MultiStepCodeBuilder(code_agent=coding_agent)
validator = CodeQualityValidator(validation_agent=security_agent)
```

## 📊 Performance

FSAs are designed for production use:
- ⚡ Fast state transitions (<2μs)
- 💾 Low memory footprint
- 🔄 Efficient parallel execution
- 📈 Scalable to complex workflows

## 🎯 Next Steps

1. Run the examples: `python cookbook/fsa/01_basic_fsa_usage.py`
2. Modify examples for your use case
3. Build custom FSAs extending the base `FSA` class
4. Combine FSAs with the Meta-FSA Orchestrator

## 🐛 Troubleshooting

### FSA stuck in state
- Check transition conditions with `debug_mode=True`
- Verify context data meets condition requirements
- Review state diagram: `fsa.get_state_diagram()`

### Orchestrator not executing FSAs
- Verify FSA dependencies are correctly specified
- Check for circular dependencies
- Enable debug mode to see execution plan

## 📝 Contributing

FSA framework follows Agno's contribution guidelines. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](../../LICENSE)

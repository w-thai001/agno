# FSA Framework - Fundamentally Sequenced Actions

A comprehensive meta-orchestration system for coordinating complex multi-step workflows, code generation, optimization, and quality validation processes within the Agno agent framework.

## 🚀 Overview

The FSA Framework provides 5 integrated tools that work together to enable sophisticated development workflows:

1. **Meta-FSA Orchestrator** - Master coordinator for FSA workflows
2. **Multi-Step Code Builder** - Incremental code construction with validation
3. **MLA Task Deconstructor** - Maximum Leverage Analysis for task prioritization
4. **RSI Code Optimizer** - Recursive Self-Improvement for code optimization
5. **Code Quality Validator** - Comprehensive quality assurance and validation

## 📦 Installation

The FSA framework is part of the Agno library:

```bash
pip install agno
```

Or for development:

```bash
git clone https://github.com/agno-agi/agno.git
cd agno
pip install -e libs/agno
```

## 🎯 Quick Start

### 1. Meta-FSA Orchestrator

Coordinate complex workflows with dependencies and parallel execution:

```python
import asyncio
from agno.fsa import FSAOrchestrator, FSA, FSAExecutor, FSAContext

class DataLoaderExecutor(FSAExecutor):
    async def execute(self, context: FSAContext):
        # Load data
        data = {"records": [1, 2, 3, 4, 5]}
        context.set("data", data)
        return data

class ProcessorExecutor(FSAExecutor):
    async def execute(self, context: FSAContext):
        # Process data
        data = context.get("data")
        processed = [x * 2 for x in data["records"]]
        return processed

# Create orchestrator
orchestrator = FSAOrchestrator()

# Add FSAs with dependencies
load_fsa = FSA(id="load", name="Load Data", executor=DataLoaderExecutor())
process_fsa = FSA(
    id="process",
    name="Process Data",
    executor=ProcessorExecutor(),
    dependencies=["load"]  # Runs after load
)

orchestrator.add_fsa(load_fsa)
orchestrator.add_fsa(process_fsa)

# Execute
results = await orchestrator.execute()
print(f"Completed: {len(results)} FSAs")
```

### 2. Multi-Step Code Builder

Build code incrementally with validation at each step:

```python
from agno.fsa import (
    BuildPlan,
    CodeLanguage,
    MultiStepCodeBuilder,
    TemplateCodeGenerator,
)
from pathlib import Path

# Create build plan
plan = BuildPlan(
    name="my_module",
    description="A Python utility module",
    language=CodeLanguage.PYTHON,
)

plan.add_artifact("utils.py", "Utility functions")
plan.add_artifact("__init__.py", "Package initialization")

# Create builder
builder = MultiStepCodeBuilder(plan, output_dir=Path("./output"))

# Add template generator
templates = {
    "utils": '''
def greet(name: str) -> str:
    """Greet a person."""
    return f"Hello, {name}!"
''',
}

generator = TemplateCodeGenerator(templates)
builder.add_generator("template", generator)
plan.artifacts[0]["template"] = "utils"

# Build
result = await builder.build()
print(f"Build success: {result['success']}")
```

### 3. MLA Task Deconstructor

Break down complex goals into optimally prioritized tasks:

```python
from agno.fsa import (
    Goal,
    Task,
    TaskCategory,
    TaskComplexity,
    ImpactMetrics,
    MLATaskDeconstructor,
)

# Create goal
goal = Goal(
    title="Build REST API",
    description="Create a REST API for user management",
)

# Add tasks
task1 = Task(
    id="design",
    title="Design API Schema",
    category=TaskCategory.PLANNING,
    complexity=TaskComplexity.MODERATE,
    estimated_hours=4.0,
    impact=ImpactMetrics(
        direct_value=8.0,
        reusability=7.0,
        enablement=9.0,
    ),
)

task2 = Task(
    id="implement",
    title="Implement Endpoints",
    category=TaskCategory.IMPLEMENTATION,
    complexity=TaskComplexity.COMPLEX,
    estimated_hours=12.0,
    impact=ImpactMetrics(direct_value=9.0),
)
task2.add_dependency("design")

goal.add_task(task1)
goal.add_task(task2)

# Deconstruct and prioritize
deconstructor = MLATaskDeconstructor()
result = deconstructor.deconstruct(goal)

# Get prioritized tasks
result.print_summary()

for task in result.get_prioritized_tasks()[:5]:
    print(f"{task.priority_rank}. {task.title} (leverage: {task.leverage_score:.1f})")
```

### 4. RSI Code Optimizer

Iteratively optimize code with self-improvement:

```python
from agno.fsa import RSICodeOptimizer

code = '''
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                result.append(item * 2)
    return result
'''

# Create optimizer
optimizer = RSICodeOptimizer()

# Optimize
result = await optimizer.optimize(
    code=code,
    max_iterations=5,
)

result.print_summary()
print(f"\nOptimized code:\n{result.optimized_code}")
```

### 5. Code Quality Validator

Validate code against quality standards:

```python
from agno.fsa import (
    QualityValidator,
    QualityGate,
)

code = '''
def example():
    eval("print('dangerous')")  # Security issue
    x = 1; y = 2  # Style issue
'''

# Create validator with quality gate
validator = QualityValidator()
gate = QualityGate(
    max_critical=0,
    max_errors=0,
    min_quality_score=80.0,
)

# Validate
result = validator.validate(code, quality_gate=gate)

result.print_summary()

if result.quality_score >= 80:
    print("✓ Code meets quality standards")
else:
    print("✗ Code needs improvement")
```

## 🔗 Integration Example

All FSAs working together in a complete workflow:

```python
import asyncio
from pathlib import Path
from agno.fsa import *

async def complete_development_workflow():
    """Complete development workflow using all FSAs."""

    # 1. TASK DECONSTRUCTION
    print("Step 1: Deconstructing project goals...")
    goal = Goal(title="Build Feature X", description="...")
    deconstructor = MLATaskDeconstructor()
    task_result = deconstructor.deconstruct(goal)

    # 2. CODE BUILDING
    print("\nStep 2: Building code...")
    plan = BuildPlan(
        name="feature_x",
        language=CodeLanguage.PYTHON,
    )
    builder = MultiStepCodeBuilder(plan, output_dir=Path("./build"))
    build_result = await builder.build()

    # 3. CODE OPTIMIZATION
    print("\nStep 3: Optimizing code...")
    optimizer = RSICodeOptimizer()
    code = build_result['artifacts']['main.py']['content']
    opt_result = await optimizer.optimize(code)

    # 4. QUALITY VALIDATION
    print("\nStep 4: Validating quality...")
    validator = QualityValidator()
    gate = QualityGate(min_quality_score=80.0)
    val_result = validator.validate(opt_result.optimized_code, quality_gate=gate)

    # 5. ORCHESTRATION
    print("\nStep 5: Final orchestration...")
    orchestrator = FSAOrchestrator()

    # Create FSA for deployment
    class DeployExecutor(FSAExecutor):
        async def execute(self, context: FSAContext):
            return {"deployed": True}

    deploy_fsa = FSA(
        id="deploy",
        name="Deploy Code",
        executor=DeployExecutor(),
    )

    orchestrator.add_fsa(deploy_fsa)
    final_results = await orchestrator.execute()

    print("\n✓ Complete workflow finished!")
    return {
        "tasks": task_result,
        "build": build_result,
        "optimization": opt_result,
        "validation": val_result,
        "deployment": final_results,
    }

# Run workflow
result = asyncio.run(complete_development_workflow())
```

## 📚 Component Documentation

### Meta-FSA Orchestrator

**Purpose**: Coordinate multiple FSAs with dependency management and parallel execution.

**Key Features**:
- Automatic dependency resolution
- Parallel execution of independent FSAs
- Retry logic with exponential backoff
- Timeout management
- Progress tracking
- State management

**Use Cases**:
- Complex multi-step workflows
- Agent coordination
- Data pipeline orchestration
- Build systems

### Multi-Step Code Builder

**Purpose**: Build code incrementally with validation at each step.

**Key Features**:
- Step-by-step construction
- Template and AI-based generation
- Validation gates
- Artifact management
- Multi-language support

**Use Cases**:
- Code generation
- Scaffolding
- Project setup
- Template instantiation

### MLA Task Deconstructor

**Purpose**: Break down complex goals using Maximum Leverage Analysis.

**Key Features**:
- Hierarchical decomposition
- Multi-dimensional impact assessment
- Leverage-based prioritization
- Dependency validation
- Goal alignment scoring

**Use Cases**:
- Project planning
- Sprint planning
- Resource allocation
- Strategic prioritization

### RSI Code Optimizer

**Purpose**: Iteratively optimize code with self-improvement.

**Key Features**:
- Multi-pass optimization
- Pattern learning
- Convergence detection
- Rollback support
- Quality metrics tracking

**Use Cases**:
- Code refactoring
- Performance optimization
- Code quality improvement
- Technical debt reduction

### Code Quality Validator

**Purpose**: Comprehensive code quality validation.

**Key Features**:
- Multi-dimensional quality checks
- Configurable rules
- Quality gates
- Auto-fix suggestions
- Severity-based reporting

**Use Cases**:
- CI/CD quality gates
- Pre-commit validation
- Code review automation
- Standards enforcement

## 🏗️ Architecture

The FSA framework follows a modular, composable architecture:

```
agno.fsa/
├── orchestrator.py       # Core FSA orchestration
├── code_builder.py       # Multi-step code building
├── mla_deconstructor.py  # Task deconstruction with MLA
├── rsi_optimizer.py      # Recursive self-improvement
├── quality_validator.py  # Code quality validation
├── examples.py           # Orchestrator examples
├── code_builder_examples.py
├── mla_deconstructor_examples.py
└── tests/
    └── test_orchestrator.py
```

## 🧪 Testing

Comprehensive test suites are provided:

```bash
# Run all FSA tests
pytest libs/agno/agno/fsa/tests/

# Run specific component tests
pytest libs/agno/agno/fsa/tests/test_orchestrator.py -v
```

## 🤝 Contributing

Contributions are welcome! To add a new FSA or improve existing ones:

1. Follow the `FSAExecutor` pattern
2. Add comprehensive tests
3. Include examples
4. Update documentation
5. Ensure integration with other FSAs

## 📖 Advanced Topics

### Custom FSA Executors

Create custom executors for specific workflows:

```python
class CustomExecutor(FSAExecutor):
    def __init__(self, config):
        self.config = config

    def validate(self, context: FSAContext) -> bool:
        # Custom validation logic
        return context.has("required_key")

    async def execute(self, context: FSAContext):
        # Custom execution logic
        result = await self.custom_operation()
        context.set("result", result)
        return result

    def on_success(self, context: FSAContext, result):
        # Post-success hook
        logger.info(f"Success: {result}")

    def on_failure(self, context: FSAContext, error: Exception):
        # Post-failure hook
        logger.error(f"Failed: {error}")
```

### Custom Validation Rules

Add custom quality validation rules:

```python
class CustomValidationRule(ValidationRule):
    def __init__(self):
        super().__init__(
            rule_id="CUSTOM001",
            dimension=QualityDimension.BEST_PRACTICES,
            severity=ViolationSeverity.WARNING,
            description="Custom rule description",
        )

    def validate(self, code: str, file_path: Optional[str] = None):
        violations = []
        # Custom validation logic
        return violations

# Add to validator
validator = QualityValidator()
validator.add_rule(CustomValidationRule())
```

## 🔧 Configuration

FSAs support extensive configuration:

```python
# Orchestrator with custom settings
orchestrator = FSAOrchestrator()

fsa = FSA(
    id="task",
    name="My Task",
    executor=MyExecutor(),
    max_retries=3,           # Retry on failure
    retry_delay=2.0,         # Delay between retries
    timeout=30.0,            # Timeout in seconds
    priority=10,             # Higher priority = runs first
    condition=lambda ctx: ctx.has("flag"),  # Conditional execution
)
```

## 📊 Monitoring and Metrics

Track FSA execution with callbacks:

```python
def progress_callback(fsa_id: str, status: FSAStatus):
    print(f"FSA {fsa_id}: {status.value}")

orchestrator.set_progress_callback(progress_callback)
```

## 🎓 Learning Resources

- **Examples**: Each component has a dedicated examples module
- **Tests**: Comprehensive test suites demonstrate usage patterns
- **Integration Example**: See complete workflow integration above

## 📄 License

Part of the Agno project. See main Agno repository for license details.

## 🙏 Acknowledgments

Built as part of the FSA Generation Sprint using MLA (Maximum Leverage Analysis) and ASEAP (Anti-Stuck Execution) principles.

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/agno-agi/agno/issues
- Community: https://community.agno.com/
- Discord: https://discord.gg/4MtYHHrgA8

---

**Version**: 1.0.0
**Status**: Production-Ready ✅
**Generated**: FSA Generation Sprint (8-hour autonomous build)

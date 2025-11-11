# FSA: Functional System Architecture

A comprehensive system for orchestrating multi-step code building with integrated AI capabilities.

## Overview

The FSA (Functional System Architecture) system provides a modular, extensible framework for breaking down complex coding tasks into manageable steps, optimizing prompts, selecting appropriate templates, routing to optimal AI models, and validating code quality.

## Architecture

```
FSA-3.1: MultiStepCodeBuilder (Orchestrator)
│
├── FSA-1.1: PromptOptimizer
│   └── Enhances prompts for clarity and context
│
├── FSA-1.2: TemplateSelector
│   └── Selects appropriate code templates and patterns
│
├── FSA-2.1: QualityValidator
│   └── Validates code quality, security, and best practices
│
└── FSA-2.2: ModelRouter
    └── Routes tasks to optimal AI models
```

## Components

### FSA-1.1: PromptOptimizer

**Purpose:** Enhances and optimizes prompts for better code generation results.

**Features:**
- Clarity enhancement - removes ambiguity
- Context enrichment - adds technical context
- Constraint specification - defines requirements
- Structure optimization - improves organization
- Best practices integration

**Usage:**
```python
from agno.fsa.prompt_optimizer import PromptOptimizer

optimizer = PromptOptimizer(debug=False)
result = optimizer.optimize(
    "Create an authentication system",
    context={
        "language": "python",
        "framework": "FastAPI",
        "stack": ["JWT", "bcrypt"]
    }
)

print(f"Optimized: {result.optimized_prompt}")
print(f"Confidence: {result.confidence}")
```

### FSA-1.2: TemplateSelector

**Purpose:** Selects appropriate code templates based on task requirements.

**Template Types:**
- API Server
- Database Layer
- Authentication
- Error Handling
- Middleware
- Routing
- Validation
- Logging

**Usage:**
```python
from agno.fsa.template_selector import TemplateSelector

selector = TemplateSelector(debug=False)
selection = selector.select_templates(
    "Build a REST API with authentication"
)

for template in selection.selected_templates:
    print(f"- {template.name}: {template.description}")
```

### FSA-2.1: QualityValidator

**Purpose:** Validates code quality through comprehensive checks.

**Validation Categories:**
- Syntax validation
- Code structure analysis
- Best practices verification
- Security checks (SQL injection, hardcoded credentials, eval usage)
- Documentation completeness

**Usage:**
```python
from agno.fsa.quality_validator import QualityValidator

validator = QualityValidator(debug=False)
result = validator.validate(
    code=my_code,
    language="python"
)

print(f"Score: {result.score}/100")
print(f"Passed: {result.passed}")
for issue in result.issues:
    print(f"- [{issue.level}] {issue.message}")
```

### FSA-2.2: ModelRouter

**Purpose:** Routes tasks to appropriate AI models based on requirements.

**Routing Factors:**
- Task complexity
- Required capabilities
- Performance requirements
- Cost considerations

**Supported Models:**
- GPT-4, GPT-3.5-turbo (OpenAI)
- Claude-3 (Opus, Sonnet, Haiku) (Anthropic)
- CodeLlama (Meta)

**Usage:**
```python
from agno.fsa.model_router import ModelRouter, ModelCapability

router = ModelRouter(debug=False)
decision = router.route(
    task_description="Implement complex authentication",
    required_capabilities=[
        ModelCapability.CODE_GENERATION,
        ModelCapability.REASONING
    ]
)

print(f"Selected: {decision.selected_model.name}")
print(f"Provider: {decision.selected_model.provider}")
```

### FSA-3.1: MultiStepCodeBuilder

**Purpose:** Orchestrates the entire multi-step code building process.

**Pipeline:**
1. Task decomposition into sequential steps
2. Prompt optimization for each step (FSA-1.1)
3. Template selection (FSA-1.2)
4. Model routing (FSA-2.2)
5. Code generation
6. Quality validation (FSA-2.1)
7. Step integration
8. Progress tracking and error recovery

**Features:**
- Automatic task decomposition
- Step dependency management
- Progress tracking
- Error recovery
- Comprehensive reporting

**Usage:**
```python
from agno.fsa.multi_step_builder import MultiStepCodeBuilder

builder = MultiStepCodeBuilder(debug=True)

result = builder.build(
    task_description="Build a REST API server with authentication, "
                    "database integration, and error handling",
    context={
        "language": "python",
        "framework": "FastAPI",
        "architecture": "microservice"
    }
)

print(result.summary)
print(f"Success: {result.success}")
print(f"Steps completed: {result.progress.completed_steps}/{result.progress.total_steps}")

if result.integrated_code:
    print(f"Generated code:\n{result.integrated_code}")
```

## Complete Example

```python
from agno.fsa import MultiStepCodeBuilder

# Initialize the builder
builder = MultiStepCodeBuilder(debug=True)

# Define your task
task = "Build a REST API server with authentication, database integration, and error handling"

# Build context
context = {
    "language": "python",
    "framework": "FastAPI",
    "stack": ["FastAPI", "SQLAlchemy", "JWT", "bcrypt"],
    "architecture": "microservice",
    "constraints": [
        "Use async/await for database operations",
        "Implement proper error handling",
        "Include request validation"
    ]
}

# Execute the build
result = builder.build(task, context)

# Check results
if result.success:
    print("✓ Build completed successfully!")
    print(f"Generated code:\n{result.integrated_code}")
else:
    print("⚠ Build completed with issues")
    for step in result.steps:
        if step.status == "failed":
            print(f"Failed step: {step.name} - {step.error}")
```

## Demo

Run the comprehensive demo to see all FSA components in action:

```bash
python examples/fsa_demo.py
```

The demo showcases:
1. Individual FSA component demonstrations
2. FSA pipeline integration
3. Complete multi-step build with sample project
4. Step decomposition visualization
5. Template selection details
6. Quality validation results
7. Progress metrics and reporting

## Key Features

### 1. Intelligent Task Decomposition
Automatically breaks complex tasks into logical, sequential steps with dependency management.

### 2. FSA Pipeline Integration
Seamlessly integrates all FSA components in an optimized pipeline:
- FSA-1.1 → FSA-1.2 → FSA-2.2 → Code Gen → FSA-2.1

### 3. Step Dependency Management
- Tracks dependencies between steps
- Ensures proper execution order
- Handles parallel execution where possible

### 4. Progress Tracking
- Real-time progress updates
- Detailed step status tracking
- Performance metrics

### 5. Error Recovery
- Graceful error handling
- Step-level failure isolation
- Comprehensive error reporting

### 6. Quality Assurance
- Multi-level validation
- Security checks
- Best practices enforcement
- Code quality scoring

### 7. Flexibility
- Customizable code generators
- Extensible template library
- Configurable validation rules
- Pluggable model routing

## Integration with Agno

The FSA system integrates seamlessly with the Agno framework:

- Uses Agno's `ReasoningStep` model for structured reasoning
- Compatible with Agno's `Workflow` system for orchestration
- Leverages Agno's logging infrastructure
- Works with Agno's agent and model systems

## Extension Points

### Custom Templates

Add your own templates to FSA-1.2:

```python
from agno.fsa.template_selector import CodeTemplate, TemplateType

custom_template = CodeTemplate(
    name="Custom Component",
    type=TemplateType.IMPLEMENTATION,
    description="Your custom component",
    pattern="# Your code pattern here",
    dependencies=["dep1", "dep2"],
    best_practices=["Practice 1", "Practice 2"],
    tags=["custom", "component"]
)

selector.templates.append(custom_template)
```

### Custom Validators

Extend FSA-2.1 with custom validation rules:

```python
from agno.fsa.quality_validator import QualityValidator

validator = QualityValidator()

# Add custom validation logic
def custom_validator(code, language):
    issues = []
    # Your validation logic
    return issues

validator._validate_custom = custom_validator
```

### Custom Models

Add models to FSA-2.2:

```python
from agno.fsa.model_router import ModelProfile, ModelCapability

custom_model = ModelProfile(
    name="custom-model",
    provider="custom-provider",
    capabilities=[ModelCapability.CODE_GENERATION],
    complexity_rating=8,
    speed_rating=9,
    cost_rating=3,
    max_tokens=32000
)

router.models.append(custom_model)
```

## Performance Considerations

- **Task Decomposition:** O(n) where n is task complexity
- **Template Selection:** O(m) where m is number of templates
- **Quality Validation:** O(k) where k is code size
- **Model Routing:** O(p) where p is number of models

Typical build times:
- Simple tasks (1-3 steps): < 1 second
- Moderate tasks (4-6 steps): 1-3 seconds
- Complex tasks (7+ steps): 3-10 seconds

## Future Enhancements

1. **Machine Learning Integration**
   - Learn from successful builds
   - Improve template selection accuracy
   - Optimize model routing decisions

2. **Parallel Execution**
   - Execute independent steps in parallel
   - Reduce overall build time

3. **Interactive Mode**
   - Allow user intervention during build
   - Manual step approval
   - Dynamic requirement adjustment

4. **Code Refinement**
   - Iterative improvement cycles
   - Automatic issue resolution
   - Test-driven refinement

5. **Extended Language Support**
   - More programming languages
   - Framework-specific templates
   - Language-specific validators

## Contributing

To contribute to the FSA system:

1. Add new templates to `template_selector.py`
2. Extend validation rules in `quality_validator.py`
3. Add model profiles to `model_router.py`
4. Improve optimization strategies in `prompt_optimizer.py`
5. Enhance orchestration logic in `multi_step_builder.py`

## License

Part of the Agno framework. See main Agno license for details.

## Support

For issues, questions, or contributions related to the FSA system, please refer to the main Agno repository.

# FSA-3.1: Multi-Step Code Builder

Orchestration layer that integrates all FSA components to build complex projects step-by-step with automatic quality validation and progress tracking.

## Overview

The Multi-Step Code Builder is the capstone component that ties together the entire FSA ecosystem:

- **FSA-1.1: Prompt Optimizer** - Optimizes prompts for each build step
- **FSA-1.2: Code Template Library** - Selects appropriate templates
- **FSA-2.1: Code Quality Validator** - Validates generated code
- **FSA-2.2: Multi-Model Orchestrator** - Routes tasks to optimal models (optional)

## Features

### Intelligent Task Decomposition
- Breaks complex requirements into sequential steps
- Analyzes requirements to determine project components
- Manages dependencies between steps
- Creates execution timeline

### Quality-Driven Build Process
- Validates each step with FSA-2.1
- Enforces minimum quality thresholds
- Automatic rollback on failures (optional)
- Comprehensive quality reporting

### Template-Based Generation
- Selects templates from FSA-1.2 library
- Matches templates to step types
- Prefers high-quality templates (EXCELLENT > GOOD)
- Falls back to minimal code generation

### Progress Tracking
- Real-time step status updates
- Execution time tracking
- Build statistics and analytics
- Detailed validation reports

## Installation

```bash
pip install agno
```

## Quick Start

```python
from agno.builder import MultiStepCodeBuilder

# Initialize builder
builder = MultiStepCodeBuilder(
    use_orchestrator=False,  # Set True to use FSA-2.2
    min_quality_score=70,     # Minimum acceptable quality
    enable_rollback=True      # Enable rollback on failures
)

# Define requirements
requirements = """
Build a REST API for a blog platform with:
- Database storage with SQLite
- API endpoints for posts and users
- Error handling and validation
- Unit tests
"""

# Build project
result = builder.buildProject(
    requirements=requirements,
    project_name="blog_api",
    language="python"
)

print(f"Build Status: {result.summary}")
print(f"Quality Score: {result.overall_quality_score}/100")
print(f"Files Generated: {len(result.generated_files)}")
```

## Core Methods

### `buildProject(requirements, project_name, language, budget)`

Build a complete project from requirements.

**Parameters:**
- `requirements` (str): Project requirements description
- `project_name` (str): Name of the project
- `language` (str): Programming language (python, javascript)
- `budget` (BudgetConstraints, optional): Budget constraints for FSA-2.2

**Returns:** `BuildResult` with all generated code and validation

```python
result = builder.buildProject(
    requirements="Build a REST API with database",
    project_name="my_api",
    language="python"
)

# Access results
print(result.success)              # True/False
print(result.completed_steps)      # Number of completed steps
print(result.overall_quality_score) # Average quality score
print(result.generated_files)      # Dict of filename -> code
```

### `decomposeTask(requirements, language)`

Decompose requirements into sequential steps.

**Parameters:**
- `requirements` (str): Project requirements
- `language` (str): Programming language

**Returns:** List of `ProjectStep` objects

```python
steps = builder.decomposeTask(
    requirements="Build API with database and auth",
    language="python"
)

for step in steps:
    print(f"{step.name} - {step.step_type.value}")
    if step.dependencies:
        print(f"  Depends on: {step.dependencies}")
```

### `executeStep(step, budget)`

Execute a single project step.

**Parameters:**
- `step` (ProjectStep): Step to execute
- `budget` (BudgetConstraints, optional): Budget constraints

**Returns:** `bool` - True if step succeeded with acceptable quality

```python
success = builder.executeStep(step)

if success:
    print(f"Code: {step.generated_code}")
    print(f"Quality: {step.quality_score}/100")
else:
    print(f"Failed: {step.error}")
```

### `validateStep(step)`

Validate a step's generated code using FSA-2.1.

**Parameters:**
- `step` (ProjectStep): Step with generated code

**Returns:** `ValidationResult` from FSA-2.1

```python
validation = builder.validateStep(step)

print(f"Overall: {validation.report.overall_score}/100")

for dim_name, dim_score in validation.report.dimensions.items():
    print(f"{dim_name}: {dim_score.score}/100")
```

### `rollback(steps, from_step)`

Rollback steps from a specific step.

**Parameters:**
- `steps` (List[ProjectStep]): All steps
- `from_step` (str): Step ID to rollback from

```python
builder.rollback(result.steps, "step_5")
```

## Project Steps

### Step Types

The builder automatically creates appropriate steps based on requirements:

| Step Type | Description | Example Templates |
|-----------|-------------|-------------------|
| `PLANNING` | Project structure and architecture | - |
| `SCHEMA_DESIGN` | Database schema design | py_db_query_good |
| `DATABASE` | Database connection utilities | py_db_query_good |
| `API_ENDPOINT` | REST API endpoints | py_api_good, js_async_good |
| `BUSINESS_LOGIC` | Core business logic | - |
| `ERROR_HANDLING` | Error handling | py_error_handling_good |
| `TESTING` | Unit tests | - |
| `DOCUMENTATION` | Documentation | - |
| `DEPLOYMENT` | Deployment config | - |

### Step Status

- `PENDING` - Not yet started
- `IN_PROGRESS` - Currently executing
- `COMPLETED` - Successfully completed
- `FAILED` - Execution failed
- `ROLLED_BACK` - Reverted

## Requirements Analysis

The builder intelligently analyzes requirements to determine needed components:

```python
# Database Detection
"database", "db", "sql", "storage", "persist"
→ Adds: Schema Design, Database Connection steps

# API Detection
"api", "endpoint", "rest", "route"
→ Adds: API Endpoints step

# Authentication Detection
"auth", "login", "user", "session"
→ Adds: Authentication steps
```

## FSA Integration

### FSA-1.1: Prompt Optimizer

Generates optimized prompts for each step (available for AI integration):

```python
# Get optimized prompt for a step
prompt = builder.prompt_optimizer.optimize_for_analysis(
    code=step.generated_code,
    language=step.language,
    analysis_type=AnalysisType.SECURITY
)
```

### FSA-1.2: Code Template Library

Automatically selects templates based on step type:

```python
# Templates selected by step type
API_ENDPOINT → py_api_good, js_async_good
DATABASE → py_db_query_good
ERROR_HANDLING → py_error_handling_good
```

### FSA-2.1: Code Quality Validator

Validates every step with multi-dimensional analysis:

```python
# Automatic validation for each step
validation = builder.validateStep(step)

# Quality dimensions checked:
# - Syntax (25%)
# - Security (25%)
# - Style (15%)
# - Performance (15%)
# - Best Practices (20%)
```

### FSA-2.2: Multi-Model Orchestrator (Optional)

Routes tasks to optimal Claude models:

```python
builder = MultiStepCodeBuilder(
    use_orchestrator=True  # Enable FSA-2.2
)

result = builder.buildProject(
    requirements="...",
    project_name="...",
    budget=BudgetConstraints(prefer_quality=True)
)
```

## Build Result

The `BuildResult` object contains comprehensive information:

```python
result = builder.buildProject(...)

# Build metrics
result.success                    # True if all steps completed
result.total_steps                # Total number of steps
result.completed_steps            # Successfully completed steps
result.failed_steps               # Failed steps
result.overall_quality_score      # Average quality score (0-100)
result.total_execution_time_ms    # Total build time

# Generated code
result.generated_files           # Dict: filename -> code
result.steps                     # List of all ProjectStep objects

# Summary
result.summary                   # Human-readable summary
```

## Examples

### Example 1: Simple API

```python
builder = MultiStepCodeBuilder(min_quality_score=70)

result = builder.buildProject(
    requirements="Build a REST API with 2 endpoints: GET /users and POST /users",
    project_name="simple_api",
    language="python"
)

# Result:
# ✓ 5 steps completed
# ✓ Quality: 96/100
# ✓ Files: api.py, database.py, errors.py, test_api.py
```

### Example 2: Complete Application

```python
requirements = """
Build a task management system with:
- SQLite database for task storage
- REST API endpoints (CRUD operations)
- Task status transitions (todo → in_progress → done)
- Input validation
- Comprehensive error handling
- Unit tests for all endpoints
"""

result = builder.buildProject(
    requirements=requirements,
    project_name="task_manager",
    language="python"
)

# Result:
# ✓ 7 steps decomposed
# ✓ All steps completed
# ✓ Overall quality: 97/100
# ✓ Generated: schema.py, database.py, api.py, logic.py, errors.py, test.py
```

### Example 3: Quality Threshold

```python
# Strict quality requirements
builder = MultiStepCodeBuilder(min_quality_score=90)

result = builder.buildProject(...)

# Only steps with 90+ quality score will be accepted
# Lower quality steps will fail and may trigger rollback
```

### Example 4: Multi-Project Build

```python
builder = MultiStepCodeBuilder()

projects = [
    ("user_service", "Build user management API"),
    ("auth_service", "Build authentication service"),
    ("notification_service", "Build notification system")
]

for name, requirements in projects:
    result = builder.buildProject(
        requirements=requirements,
        project_name=name,
        language="python"
    )
    print(f"{name}: {result.summary}")

# Get overall statistics
stats = builder.get_build_statistics()
print(f"Success rate: {stats['success_rate']*100}%")
```

## Build Statistics

Track performance across multiple builds:

```python
stats = builder.get_build_statistics()

print(f"Total Steps: {stats['total_steps_executed']}")
print(f"Completed: {stats['completed_steps']}")
print(f"Failed: {stats['failed_steps']}")
print(f"Success Rate: {stats['success_rate']*100:.1f}%")
print(f"Avg Quality: {stats['average_quality_score']:.1f}/100")
```

## Configuration

### Quality Thresholds

```python
# Lenient (50+ quality)
builder = MultiStepCodeBuilder(min_quality_score=50)

# Standard (70+ quality)
builder = MultiStepCodeBuilder(min_quality_score=70)

# Strict (90+ quality)
builder = MultiStepCodeBuilder(min_quality_score=90)
```

### Rollback Behavior

```python
# Enable automatic rollback on failures
builder = MultiStepCodeBuilder(enable_rollback=True)

# Disable rollback (continue despite failures)
builder = MultiStepCodeBuilder(enable_rollback=False)
```

### Model Orchestration

```python
# Use FSA-2.2 for optimal model routing
builder = MultiStepCodeBuilder(
    use_orchestrator=True,
    min_quality_score=80
)

# With budget constraints
result = builder.buildProject(
    requirements="...",
    project_name="...",
    budget=BudgetConstraints(
        prefer_speed=True,
        max_cost_per_task=0.05
    )
)
```

## Running the Demo

```bash
python cookbook/builder/multi_step_demo.py
```

**Demo Scenarios:**
1. **Task Decomposition** - Breaking requirements into steps
2. **Simple Project** - Building basic API
3. **Complex Project** - Complete REST API with database
4. **FSA Integration** - Demonstrating all component integration
5. **Build Statistics** - Tracking multiple builds
6. **Quality Thresholds** - Testing different thresholds

## Sample Output

```
================================================================================
  BUILD SUMMARY
================================================================================

Build SUCCESS: task_management_api
Steps: 7/7 completed
Overall Quality: 97.1/100

Total Steps: 7
Completed: 7
Failed: 0
Overall Quality Score: 97.1/100
Total Execution Time: 45ms
Success: YES ✓

================================================================================
  STEP EXECUTION TIMELINE
================================================================================

✓ Step 1/7: Project Planning
   Type: planning
   Status: COMPLETED (quality: 95/100)
   Execution time: 3ms

✓ Step 2/7: Database Schema Design
   Type: schema_design
   Status: COMPLETED (quality: 98/100)
   Dependencies: step_1
   Execution time: 7ms

✓ Step 3/7: Database Connection
   Type: database
   Status: COMPLETED (quality: 98/100)
   Dependencies: step_2
   Execution time: 6ms

[... more steps ...]

================================================================================
  GENERATED FILES
================================================================================

📄 schema.py
   Size: 1036 characters
   Lines: 47
   Preview:
   import sqlite3
   from typing import Optional, Dict, Any
   ...
```

## Architecture

```
MultiStepCodeBuilder
├── buildProject()
│   ├── decomposeTask() → List[ProjectStep]
│   ├── For each step:
│   │   ├── Check dependencies
│   │   ├── Get templates (FSA-1.2)
│   │   ├── Generate code
│   │   ├── Validate (FSA-2.1)
│   │   └── Track progress
│   └── Generate BuildResult
├── executeStep()
│   ├── _get_relevant_templates() → FSA-1.2
│   ├── _generate_code_for_step()
│   └── validateStep() → FSA-2.1
└── get_build_statistics()
```

## Best Practices

1. **Clear Requirements** - Provide detailed, specific requirements
2. **Appropriate Thresholds** - Set realistic quality thresholds
3. **Enable Tracking** - Use statistics to monitor performance
4. **Review Generated Code** - Always review before production use
5. **Iterate** - Refine requirements based on results

## Limitations

- Template-based generation (production would use LLM)
- Limited to predefined step types
- Requires manual review of generated code
- FSA-2.2 integration requires API key

## Future Enhancements

- AI-powered code generation
- Custom step type definitions
- Interactive step refinement
- Automated testing execution
- Deployment automation

## License

Same as the parent Agno project.

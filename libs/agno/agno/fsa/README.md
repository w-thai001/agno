# FSA Framework

Production-ready Finite State Agent Framework for the Agno ecosystem.

## Overview

The FSA Framework provides a comprehensive system for building, managing, and orchestrating complex agent workflows with:

- **Centralized Registry**: Dependency injection and module management
- **Pipeline Orchestration**: Dynamic workflow construction with parallel execution
- **Production Features**: Caching, monitoring, rate limiting, and error recovery
- **CLI Tools**: Command-line interface for all FSA operations
- **Comprehensive Testing**: Integration tests and performance benchmarks

## Quick Start

### Installation

```bash
cd libs/agno
pip install -e .
```

### Basic Usage

```python
from agno.fsa import FSARegistry, FSAPipeline, FSAPipelineManager

# Register FSA module
registry = FSARegistry()
registry.register(
    name="my_module",
    version="1.0.0",
    module_class=MyModuleClass,
)

# Create pipeline
pipeline = FSAPipeline(name="workflow", registry=registry)
pipeline.add_stage(
    name="process",
    fsa_module_name="my_module",
    inputs={"data": "input"},
)

# Execute
manager = FSAPipelineManager(registry=registry)
result = manager.execute_pipeline(pipeline)

if result.is_successful():
    print("Success!")
```

### CLI Usage

```bash
# Initialize configuration
python -m agno.fsa init

# List registered modules
python -m agno.fsa list

# Check health
python -m agno.fsa health

# Execute pipeline
python -m agno.fsa orchestrate my_pipeline
```

## Components

### 1. FSA Registry (`registry.py`)

Central registration system with:
- Module registration with version management
- Dependency injection and resolution
- Lazy loading for performance
- Health monitoring
- Thread-safe operations

### 2. FSA Pipeline Manager (`pipeline_manager.py`)

Pipeline orchestration with:
- Dynamic pipeline construction
- Parallel execution of independent stages
- Error recovery and retry logic
- Result caching
- Performance metrics collection

### 3. FSA CLI (`cli.py`)

Command-line interface with:
- Pipeline management commands
- Health checking
- Performance optimization
- Configuration validation
- Interactive workflows

### 4. Production Configuration (`config/fsa_production_config.py`)

Environment-specific settings:
- Development, staging, production, test configs
- Rate limiting configuration
- Logging and monitoring setup
- Resource allocation policies
- Error handling strategies

## Architecture

```
FSARegistry
    ↓ (manages modules)
FSAPipelineManager
    ↓ (orchestrates execution)
FSAPipeline
    ↓ (defines workflow)
FSA Modules (user-defined)
```

## Performance

Designed for production with:
- Registry lookup: < 1ms avg
- Pipeline overhead: < 10ms avg
- Health checks: < 5ms avg
- Parallel speedup: 2-3x with 4 workers
- Memory efficient: < 50KB per execution

## Documentation

- **Framework Guide**: See `docs/fsa/FSA-FRAMEWORK-GUIDE.md`
- **Examples**: See `examples/fsa_integration_example.py`
- **Benchmarks**: See `examples/fsa_benchmark.py`
- **Tests**: See `tests/fsa/test_fsa_integration.py`

## Testing

```bash
# Run all tests
pytest tests/fsa/test_fsa_integration.py -v

# Run specific test class
pytest tests/fsa/test_fsa_integration.py::TestFSARegistry -v

# Run with coverage
pytest tests/fsa/ --cov=agno.fsa --cov-report=html
```

## Examples

### Example 1: Simple Module

```python
class SimpleCalculator:
    def execute(self, a: int, b: int) -> int:
        return a + b

    def health_check(self) -> bool:
        return True

registry = FSARegistry()
registry.register("calculator", "1.0.0", module_class=SimpleCalculator)

calc = registry.get("calculator")
result = calc.execute(a=5, b=3)
```

### Example 2: Pipeline with Dependencies

```python
pipeline = FSAPipeline(name="data_processing")

pipeline.add_stage("extract", fsa_module_name="extractor")
pipeline.add_stage("validate", fsa_module_name="validator", depends_on=["extract"])
pipeline.add_stage("transform", fsa_module_name="transformer", depends_on=["validate"])

result = manager.execute_pipeline(pipeline)
```

### Example 3: Parallel Execution

```python
# These stages run in parallel
pipeline.add_stage("validate_format", fsa_module_name="format_validator")
pipeline.add_stage("validate_schema", fsa_module_name="schema_validator")

# This stage waits for both
pipeline.add_stage("process", fsa_module_name="processor",
                  depends_on=["validate_format", "validate_schema"])
```

## Configuration

### Environment Variables

```bash
export FSA_ENVIRONMENT=production
export REDIS_URL=redis://localhost:6379
export FSA_LOG_LEVEL=INFO
```

### Configuration File (`.fsarc.json`)

```json
{
  "version": "1.0.0",
  "modules": {
    "my_module": {
      "version": "1.0.0",
      "path": "package.module.ClassName"
    }
  },
  "pipelines": {
    "my_pipeline": {
      "stages": [
        {
          "name": "stage1",
          "fsa_module": "my_module",
          "inputs": {"key": "value"}
        }
      ]
    }
  }
}
```

## Production Deployment

### Checklist

- [ ] Set `FSA_ENVIRONMENT=production`
- [ ] Configure Redis for caching
- [ ] Enable monitoring (Prometheus/Datadog)
- [ ] Set up authentication
- [ ] Configure rate limiting
- [ ] Enable logging
- [ ] Run load tests
- [ ] Set up alerts

### Production Config

```python
from agno.config import get_fsa_config

config = get_fsa_config(env="production")
config.apply_logging_config()
```

## API Reference

### FSARegistry

```python
registry.register(name, version, module_class, dependencies, lazy_load)
registry.get(name, **init_kwargs)
registry.health_check(name, force=False)
registry.health_check_all()
registry.list_modules()
registry.unregister(name)
```

### FSAPipeline

```python
pipeline.add_stage(name, fsa_module_name, inputs, depends_on, retry_config)
pipeline.remove_stage(name)
pipeline.get_execution_order()
```

### FSAPipelineManager

```python
manager.execute_pipeline(pipeline, initial_inputs, use_cache)
manager.get_metrics(pipeline_name)
manager.clear_cache(pipeline_id)
```

## Troubleshooting

### Module not registered

```python
# Ensure module is registered before use
registry.register(name="my_module", version="1.0.0", module_class=MyModule)
```

### Circular dependency

```python
# Remove circular references in dependencies
# Bad: A depends on B, B depends on A
# Good: A depends on B, B depends on nothing
```

### Performance issues

```python
# Enable caching
manager = FSAPipelineManager(enable_caching=True)

# Use lazy loading
registry.register(name="module", lazy_load=True, ...)

# Increase workers
manager = FSAPipelineManager(max_workers=8)
```

## Contributing

When contributing FSA modules:

1. Follow the FSA interface:
   - Implement `execute(**kwargs)` method
   - Optional: Implement `health_check()` method
   - Accept `dependencies` in `__init__`

2. Add tests:
   - Unit tests for your module
   - Integration tests in the pipeline
   - Performance benchmarks

3. Document:
   - Module purpose and usage
   - Input/output formats
   - Dependencies required

## License

Part of the Agno project - see LICENSE file.

## Version

1.0.0

## Authors

Agno Team
